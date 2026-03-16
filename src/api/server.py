"""REST API server for Job Search Agent (FastAPI + Supabase)"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.config.settings import config
from src.core.agent import JobSearchAgent
from src.models.job import Job, UserProfile, JobSearchCriteria
from src.api.auth import AuthUser, get_current_user
from src.db import supabase_client as db
from src.services.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf

logger = logging.getLogger(__name__)

# ── Pydantic request models ─────────────────────────────────

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    experience: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)


class CriteriaUpdate(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    experience_levels: List[str] = Field(default_factory=list)
    job_types: List[str] = Field(default_factory=list)
    exclude_terms: List[str] = Field(default_factory=list)


class GenerateFromJDRequest(BaseModel):
    job_description: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None


class JobStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Job Search AI Agent API",
    description="AI-powered job search with resume and cover letter generation",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.app.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init agent (only for Ollama / job-search services)
_agent: Optional[JobSearchAgent] = None


def get_agent() -> JobSearchAgent:
    global _agent
    if _agent is None:
        _agent = JobSearchAgent()
    return _agent


# ── Routes ───────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    health = get_agent().health_check()
    if not health["overall"]:
        raise HTTPException(status_code=503, detail=health)
    return health


# ── Profile ──────────────────────────────────────────────────

@app.get("/api/profile")
def get_profile(user: AuthUser = Depends(get_current_user)):
    row = db.get_profile(user.id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "name": row.get("name"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "linkedin": row.get("linkedin"),
        "location": row.get("location"),
        "experience": row.get("experience", []),
        "projects": row.get("projects", []),
        "certifications": row.get("certifications", []),
        "education": row.get("education", []),
        "skills": row.get("skills", []),
    }


@app.post("/api/profile")
def update_profile(body: ProfileUpdate, user: AuthUser = Depends(get_current_user)):
    db.upsert_profile(user.id, {
        "name": body.name,
        "email": body.email,
        "phone": body.phone,
        "linkedin": body.linkedin,
        "location": body.location,
        "experience": body.experience or [],
        "projects": body.projects or [],
        "certifications": body.certifications or [],
        "education": body.education or [],
        "skills": body.skills or [],
    })
    return {"message": "Profile saved"}


# ── Search Criteria ──────────────────────────────────────────

@app.get("/api/criteria")
def get_criteria(user: AuthUser = Depends(get_current_user)):
    row = db.get_criteria(user.id)
    if not row:
        return {
            "keywords": [],
            "locations": [],
            "experience_levels": [],
            "job_types": [],
            "exclude_terms": [],
        }
    return {
        "keywords": row.get("keywords", []),
        "locations": row.get("locations", []),
        "experience_levels": row.get("experience_levels", []),
        "job_types": row.get("job_types", []),
        "exclude_terms": row.get("exclude_terms", []),
    }


@app.post("/api/criteria")
def update_criteria(body: CriteriaUpdate, user: AuthUser = Depends(get_current_user)):
    db.upsert_criteria(user.id, {
        "keywords": body.keywords or [],
        "locations": body.locations or [],
        "experience_levels": body.experience_levels or [],
        "job_types": body.job_types or [],
        "exclude_terms": body.exclude_terms or [],
    })
    return {"message": "Criteria saved"}


# ── Jobs ─────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs(user: AuthUser = Depends(get_current_user)):
    rows = db.get_jobs(user.id)
    return {"jobs": rows}


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str, user: AuthUser = Depends(get_current_user)):
    row = db.get_job(user.id, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return row


@app.patch("/api/jobs/{job_id}")
def update_job_status(job_id: str, body: JobStatusUpdate, user: AuthUser = Depends(get_current_user)):
    data: Dict[str, Any] = {"status": body.status}
    if body.notes is not None:
        data["notes"] = body.notes
    updated = db.update_job(user.id, job_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job updated"}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, user: AuthUser = Depends(get_current_user)):
    db.get_service_client().table("jobs").delete().eq("id", job_id).eq("user_id", user.id).execute()
    return {"message": "Job deleted"}


# ── Helpers ───────────────────────────────────────────────────

def _profile_from_row(row: dict) -> UserProfile:
    return UserProfile(
        name=row.get("name"),
        email=row.get("email"),
        phone=row.get("phone"),
        linkedin=row.get("linkedin"),
        location=row.get("location"),
        experience=row.get("experience", []),
        projects=row.get("projects", []),
        certifications=row.get("certifications", []),
        education=row.get("education", []),
        skills=row.get("skills", []),
    )

def _contact_from_row(row: dict) -> dict:
    return {k: row.get(k) for k in ("name", "email", "phone", "linkedin", "location")}


# ── Generate from JD (on-demand) ─────────────────────────────

@app.post("/api/generate-from-jd")
def generate_from_jd(body: GenerateFromJDRequest, user: AuthUser = Depends(get_current_user)):
    if not body.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required")

    profile_row = db.get_profile(user.id)
    if not profile_row:
        raise HTTPException(status_code=400, detail="Save your profile first.")

    profile = _profile_from_row(profile_row)

    title = (body.title or "").strip() or "Role"
    company = (body.company or "").strip() or "Company"
    location = (body.location or "").strip() or ""

    job = Job(
        title=title,
        company=company,
        location=location,
        description=body.job_description.strip(),
        url="",
    )

    resume_data, cover_data = get_agent().doc_generator.generate_structured_application(job, profile)
    logger.info(f"Resume keys: {list(resume_data.keys()) if resume_data else 'empty'}")
    logger.info(f"Cover letter keys: {list(cover_data.keys()) if cover_data else 'empty'}, body len: {len(cover_data.get('body', []))}")

    saved = db.upsert_job(user.id, {
        "title": title,
        "company": company,
        "location": location,
        "description": body.job_description.strip(),
        "url": "",
        "source": "manual",
        "added_by": "user",
        "resume_text": json.dumps(resume_data),
        "cover_letter_text": json.dumps(cover_data),
    })

    return {
        "id": saved.get("id"),
        "resume_data": resume_data,
        "cover_letter_data": cover_data,
        "title": title,
        "company": company,
    }


# ── PDF download endpoints ───────────────────────────────────

@app.get("/api/jobs/{job_id}/resume.pdf")
def download_resume_pdf(job_id: str, user: AuthUser = Depends(get_current_user)):
    job_row = db.get_job(user.id, job_id)
    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found")

    raw = job_row.get("resume_text", "")
    if not raw:
        raise HTTPException(status_code=404, detail="No resume generated for this job")

    try:
        resume_data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="Resume data is not in structured format")

    profile_row = db.get_profile(user.id) or {}
    contact = _contact_from_row(profile_row)

    pdf_bytes = generate_resume_pdf(contact, resume_data)
    filename = f"resume-{job_row.get('company', 'company').replace(' ', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/jobs/{job_id}/cover-letter.pdf")
def download_cover_letter_pdf(job_id: str, user: AuthUser = Depends(get_current_user)):
    job_row = db.get_job(user.id, job_id)
    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found")

    raw = job_row.get("cover_letter_text", "")
    if not raw:
        raise HTTPException(status_code=404, detail="No cover letter generated for this job")

    try:
        cover_data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail="Cover letter data is not in structured format")

    profile_row = db.get_profile(user.id) or {}
    contact = _contact_from_row(profile_row)

    pdf_bytes = generate_cover_letter_pdf(contact, cover_data)
    filename = f"cover-letter-{job_row.get('company', 'company').replace(' ', '-')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Search (agent-powered) ──────────────────────────────────

@app.post("/api/search")
def search(user: AuthUser = Depends(get_current_user)):
    criteria_row = db.get_criteria(user.id)
    if not criteria_row:
        raise HTTPException(status_code=400, detail="Set search criteria first")

    profile_row = db.get_profile(user.id)
    if not profile_row:
        raise HTTPException(status_code=400, detail="Set profile first")

    criteria = JobSearchCriteria(
        keywords=criteria_row.get("keywords", ["software engineer"]),
        locations=criteria_row.get("locations", ["remote"]),
        experience_levels=criteria_row.get("experience_levels", ["entry"]),
        job_types=criteria_row.get("job_types", ["full-time"]),
        exclude_terms=criteria_row.get("exclude_terms", []),
    )

    profile = _profile_from_row(profile_row)

    agent = get_agent()

    jobs = agent.job_search.search_jobs(criteria)
    if not jobs:
        return {"message": "No jobs found", "count": 0}

    top_jobs = agent.job_ranker.rank_jobs(
        jobs, criteria.keywords, config.app.top_n_jobs
    )

    stored = 0
    for j in top_jobs:
        try:
            resume, cover = agent.doc_generator.generate_application(j, profile)
        except Exception as e:
            logger.error(f"Doc generation failed for {j.title}: {e}")
            resume, cover = "", ""

        db.upsert_job(user.id, {
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "description": j.description,
            "url": j.url,
            "posted_date": j.posted_date,
            "salary_range": j.salary_range,
            "job_type": j.job_type,
            "source": j.source,
            "added_by": "agent",
            "resume_text": resume,
            "cover_letter_text": cover,
        })
        stored += 1

    return {"message": f"Found and processed {stored} jobs", "count": stored}


# ── Run ──────────────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    import os, uvicorn
    port = int(os.getenv("PORT", str(port)))
    logger.info(f"Starting Job Agent API on {host}:{port}")
    uvicorn.run("src.api.server:app", host=host, port=port, reload=debug)

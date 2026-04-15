"""REST API for the job search agent (FastAPI + Supabase)."""

import json
import logging
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src import agent, db, llm, pdf
from src.auth import AuthUser, get_current_user
from src.config import settings
from src.models import Job, UserProfile

logger = logging.getLogger(__name__)


# ── Request models ──────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    experience: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class CriteriaUpdate(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    experience_levels: list[str] = Field(default_factory=list)
    job_types: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)


class GenerateFromJDRequest(BaseModel):
    job_description: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None


class JobStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


# ── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Job Search AI Agent API",
    description="AI-powered job search with resume and cover letter generation",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────────

@app.get("/api/health")
def health():
    result = agent.health_check()
    if not result["overall"]:
        raise HTTPException(status_code=503, detail=result)
    return result


# ── Profile ─────────────────────────────────────────────────

_PROFILE_FIELDS = ("name", "email", "phone", "linkedin", "location",
                   "experience", "projects", "certifications", "education", "skills")


@app.get("/api/profile")
def get_profile(user: AuthUser = Depends(get_current_user)):
    row = db.get_profile(user.id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {k: row.get(k, [] if k in ("experience", "projects", "certifications", "education", "skills") else None)
            for k in _PROFILE_FIELDS}


@app.post("/api/profile")
def update_profile(body: ProfileUpdate, user: AuthUser = Depends(get_current_user)):
    db.upsert_profile(user.id, body.model_dump())
    return {"message": "Profile saved"}


# ── Search criteria ─────────────────────────────────────────

_CRITERIA_FIELDS = ("keywords", "locations", "experience_levels", "job_types", "exclude_terms")


@app.get("/api/criteria")
def get_criteria(user: AuthUser = Depends(get_current_user)):
    row = db.get_criteria(user.id) or {}
    return {k: row.get(k, []) for k in _CRITERIA_FIELDS}


@app.post("/api/criteria")
def update_criteria(body: CriteriaUpdate, user: AuthUser = Depends(get_current_user)):
    db.upsert_criteria(user.id, body.model_dump())
    return {"message": "Criteria saved"}


# ── Jobs ────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs(user: AuthUser = Depends(get_current_user)):
    return {"jobs": db.get_jobs(user.id)}


@app.get("/api/jobs/filtered")
def list_jobs_filtered(
    added_by: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: AuthUser = Depends(get_current_user),
):
    return {"jobs": db.get_jobs_filtered(user.id, added_by=added_by, date_from=date_from, date_to=date_to)}


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str, user: AuthUser = Depends(get_current_user)):
    row = db.get_job(user.id, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    return row


@app.patch("/api/jobs/{job_id}")
def update_job_status(job_id: str, body: JobStatusUpdate, user: AuthUser = Depends(get_current_user)):
    data: dict[str, Any] = {"status": body.status}
    if body.notes is not None:
        data["notes"] = body.notes
    if not db.update_job(user.id, job_id, data):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job updated"}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, user: AuthUser = Depends(get_current_user)):
    db.delete_job(user.id, job_id)
    return {"message": "Job deleted"}


# ── Generate from JD (on-demand) ────────────────────────────

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
    location = (body.location or "").strip()
    description = body.job_description.strip()

    job = Job(title=title, company=company, location=location, description=description, url="")
    resume_data, cover_data = llm.generate_documents(job, profile)

    saved = db.upsert_job(user.id, {
        "title": title, "company": company, "location": location,
        "description": description, "url": "",
        "source": "manual", "added_by": "user",
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


# ── PDF downloads ───────────────────────────────────────────

@app.get("/api/jobs/{job_id}/resume.pdf")
def download_resume(job_id: str, user: AuthUser = Depends(get_current_user)):
    return _render_pdf(user.id, job_id, doc_type="resume")


@app.get("/api/jobs/{job_id}/cover-letter.pdf")
def download_cover_letter(job_id: str, user: AuthUser = Depends(get_current_user)):
    return _render_pdf(user.id, job_id, doc_type="cover")


def _render_pdf(user_id: str, job_id: str, doc_type: str) -> Response:
    job_row = db.get_job(user_id, job_id)
    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found")

    field = "resume_text" if doc_type == "resume" else "cover_letter_text"
    raw = job_row.get(field, "")
    if not raw:
        raise HTTPException(status_code=404, detail=f"No {doc_type} generated for this job")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=422, detail=f"{doc_type} data is not structured")

    contact = {k: (db.get_profile(user_id) or {}).get(k)
               for k in ("name", "email", "phone", "linkedin", "location")}

    pdf_bytes = (pdf.render_resume if doc_type == "resume" else pdf.render_cover_letter)(contact, data)
    company = job_row.get("company", "company").replace(" ", "-")
    filename = f"{doc_type}-{company}.pdf" if doc_type == "resume" else f"cover-letter-{company}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Search / agent control ──────────────────────────────────

@app.post("/api/search")
def search(user: AuthUser = Depends(get_current_user)):
    if not db.get_criteria(user.id):
        raise HTTPException(status_code=400, detail="Set search criteria first")
    if not db.get_profile(user.id):
        raise HTTPException(status_code=400, detail="Set profile first")
    agent.runner().run_once_for_user(user.id)
    return {"message": "Agent search started.", "count": 0}


@app.post("/api/agent/start")
def agent_start(user: AuthUser = Depends(get_current_user)):
    r = agent.runner()
    r.start()
    return {"message": "Background agent started", **r.status()}


@app.post("/api/agent/stop")
def agent_stop(user: AuthUser = Depends(get_current_user)):
    r = agent.runner()
    r.stop()
    return {"message": "Background agent stop requested", **r.status()}


@app.get("/api/agent/status")
def agent_status(user: AuthUser = Depends(get_current_user)):
    return {**agent.runner().status(), "last_run": db.get_latest_agent_run(user.id)}


# ── Helpers ─────────────────────────────────────────────────

def _profile_from_row(row: dict) -> UserProfile:
    return UserProfile(
        name=row.get("name"), email=row.get("email"), phone=row.get("phone"),
        linkedin=row.get("linkedin"), location=row.get("location"),
        experience=row.get("experience", []),
        projects=row.get("projects", []),
        certifications=row.get("certifications", []),
        education=row.get("education", []),
        skills=row.get("skills", []),
    )


# ── Entry point ─────────────────────────────────────────────

def run(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    import os
    import uvicorn
    port = int(os.getenv("PORT", str(port)))
    logger.info(f"Starting Job Agent API on {host}:{port}")
    uvicorn.run("src.api:app", host=host, port=port, reload=debug)

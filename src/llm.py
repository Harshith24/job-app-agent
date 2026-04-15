"""Ollama LLM: ranking, document generation, relevance scoring."""

import json
import logging
import re
import time
from typing import Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import Job, UserProfile

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    pass


# ── Low-level client ─────────────────────────────────────────

class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def health_check(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((requests.RequestException, OllamaError)),
    )
    def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7, json_mode: bool = False) -> str:
        start = time.time()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=settings.request_timeout,
            )
            resp.raise_for_status()
        except requests.Timeout as e:
            raise OllamaError("Request timeout") from e
        except requests.RequestException as e:
            raise OllamaError(f"Request failed: {e}") from e

        text = (resp.json().get("response") or "").strip()
        logger.info(f"Ollama responded in {time.time() - start:.2f}s")
        if not text:
            raise OllamaError("Empty response from Ollama")
        return text


_client: Optional[OllamaClient] = None


def client() -> OllamaClient:
    global _client
    if _client is None:
        _client = OllamaClient(settings.ollama_url, settings.ollama_model)
    return _client


def health_check() -> bool:
    return client().health_check()


# ── Job ranking ──────────────────────────────────────────────

def rank_jobs(jobs: list[Job], keywords: list[str], top_n: int) -> list[Job]:
    """Rank jobs by relevance. Falls back to keyword scoring if LLM fails."""
    if not jobs:
        return []

    try:
        ranked = _llm_rank(jobs, keywords)
        if ranked:
            logger.info(f"LLM ranked {len(ranked)} jobs")
            return ranked[:top_n]
    except Exception as e:
        logger.warning(f"LLM ranking failed, falling back to keyword ranking: {e}")

    return _keyword_rank(jobs, keywords)[:top_n]


def _llm_rank(jobs: list[Job], keywords: list[str]) -> list[Job]:
    descriptions = "\n".join(
        f"{i + 1}. {j.title} at {j.company} - {j.location} - {(j.description or '')[:300]}"
        for i, j in enumerate(jobs)
    )
    prompt = f"""You are a job search assistant. Rank these jobs by relevance to the criteria.

CRITERIA:
{", ".join(keywords)}

JOBS:
{descriptions}

Respond with job indices (1-based) separated by commas, most relevant first. No other text."""

    raw = client().generate(prompt, max_tokens=500, temperature=0.1)

    seen: set[int] = set()
    ordered: list[Job] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(jobs) and idx not in seen:
                seen.add(idx)
                ordered.append(jobs[idx])
    return ordered


def _keyword_rank(jobs: list[Job], keywords: list[str]) -> list[Job]:
    kw_lower = [k.lower() for k in keywords]

    def score(job: Job) -> int:
        text = f"{job.title} {job.description} {job.company}".lower()
        return sum(1 for k in kw_lower if k in text)

    return sorted(jobs, key=score, reverse=True)


# ── Relevance scoring ────────────────────────────────────────

def score_relevance(job: Job, profile: UserProfile) -> int:
    """Return a 0-100 relevance score for (job, profile)."""
    prompt = f"""You are a job-matching expert. Rate how well this job matches the candidate (0-100).

Scoring:
- 90-100: Almost perfect match
- 70-89: Strong match — most key skills overlap
- 50-69: Partial match — some skill overlap
- 30-49: Weak match — different specialisation
- 0-29: Poor match — unrelated field

Consider: skills overlap, role type alignment, seniority, applicability.

JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{(job.description or "")[:2000]}

CANDIDATE PROFILE:
{profile.to_markdown()}

Respond with ONLY a single integer between 0 and 100."""

    try:
        raw = client().generate(prompt, max_tokens=20, temperature=0.1)
    except Exception as e:
        logger.warning(f"Relevance scoring failed for {job.title}: {e}")
        return 0

    nums = re.findall(r"\d+", raw.strip())
    return max(0, min(100, int(nums[0]))) if nums else 0


# ── Document generation ──────────────────────────────────────

def generate_documents(job: Job, profile: UserProfile) -> tuple[dict, dict]:
    """Generate a structured resume + cover letter for the job."""
    try:
        raw_resume = client().generate(
            _resume_prompt(job, profile), max_tokens=8192, temperature=0.25, json_mode=True,
        )
        resume = _parse_json(raw_resume, "resume") or _fallback_resume(profile)
        _validate_resume(resume, profile)
    except Exception as e:
        logger.error(f"Resume generation failed for {job.title}: {e}")
        resume = _fallback_resume(profile)

    try:
        raw_cover = client().generate(
            _cover_prompt(job, profile), max_tokens=4096, temperature=0.35, json_mode=True,
        )
        cover = _parse_json(raw_cover, "cover_letter") or _fallback_cover()
    except Exception as e:
        logger.error(f"Cover letter generation failed for {job.title}: {e}")
        cover = _fallback_cover()

    logger.info(f"Generated docs for: {job.title} @ {job.company}")
    return resume, cover


def _validate_resume(resume: dict, profile: UserProfile):
    """Patch empty sections by falling back to raw profile data."""
    if profile.experience and not resume.get("experience"):
        logger.warning("Resume has empty experience — injecting from profile")
        resume["experience"] = [str(e) for e in profile.experience]
    if profile.education and not resume.get("education"):
        logger.warning("Resume has empty education — injecting from profile")
        resume["education"] = [str(e) for e in profile.education]
    if profile.skills and not resume.get("skills"):
        logger.warning("Resume has empty skills — injecting from profile")
        resume["skills"] = list(profile.skills)
    if profile.projects and not resume.get("projects"):
        logger.warning("Resume has empty projects — injecting from profile")
        resume["projects"] = [str(p) for p in profile.projects]
    certs = profile.certifications
    if certs and not resume.get("certifications"):
        skills = resume.get("skills", [])
        cert_line = "Certifications: " + ", ".join(certs)
        if not any("certification" in s.lower() for s in skills):
            skills.insert(0, cert_line)
            resume["skills"] = skills


def _resume_prompt(job: Job, profile: UserProfile) -> str:
    return f"""You are a senior technical resume writer. Produce a tailored, ATS-friendly resume as JSON.

CANDIDATE PROFILE (source of truth — do NOT invent anything not stated here):
{profile.to_markdown()}

TARGET JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description}

Output a JSON object matching this EXACT schema (every field is required):
{{
  "education": [
    {{
      "school": "University name from profile",
      "degree": "Full degree name with focus/concentration if any",
      "year": "Graduation date, e.g. May 2026",
      "location": "City, State from profile"
    }}
  ],
  "skills": [
    "Certifications: AWS Solutions Architect, etc.",
    "Programming: Python, Java, Go, etc.",
    "Cloud/Infra: AWS, Azure, Docker, Kubernetes, etc.",
    "Cybersecurity: Penetration Testing, etc."
  ],
  "experience": [
    {{
      "title": "Exact role title from profile (include parenthetical specialisation if present)",
      "company": "Exact company name from profile",
      "location": "City, State from profile",
      "duration": "Start date - End date (e.g. August 2025 - December 2025)",
      "bullets": [
        "Action-verb + what you did + technology used + quantified impact (%, count, $, time saved). 20-40 words per bullet.",
        "Use strong verbs: Engineered, Strengthened, Accelerated, Scaled, Reduced, Automated, Mitigated, Implemented",
        "Mirror terminology from the JD where the candidate's profile supports it",
        "Bold key terms by wrapping them in **double asterisks** for emphasis"
      ]
    }}
  ],
  "projects": [
    {{
      "name": "Project name from profile",
      "type": "Personal Project or Academic Project or similar",
      "dates": "Start - End or Start - Present",
      "location": "City, State",
      "bullets": [
        "What you built + technology stack + outcome. 20-40 words.",
        "Each project should have 2-4 bullets describing what was built and technologies used"
      ]
    }}
  ]
}}

HARD RULES:
- Use ONLY facts present in the candidate profile. Do NOT invent companies, dates, metrics, or tech.
- Every experience entry from the profile MUST appear with 3-5 detailed bullets each. NEVER return an empty experience array.
- Every education entry MUST appear. NEVER return an empty education array.
- Every project MUST appear with 2-4 bullets each. NEVER return an empty projects array.
- ALL skills MUST appear, grouped by category (e.g. "Programming: Python, Java, Go"). Include certifications as a skill category.
- Bullets MUST be detailed (20-40 words each) and quantified when the profile provides numbers.
- Reorder and reword content to emphasize what the JD asks for. Do not drop entries just because they don't match perfectly.
- You MUST return the COMPLETE JSON with ALL fields fully populated. Do NOT truncate or cut off.
- Output ONLY the JSON object. No markdown fences. No explanatory text."""


def _cover_prompt(job: Job, profile: UserProfile) -> str:
    return f"""You are a senior cover-letter writer. Produce a tailored letter as JSON.

CANDIDATE PROFILE (source of truth):
{profile.to_markdown()}

TARGET JOB:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description}

Output JSON matching this schema:
{{
  "greeting": "Dear {job.company} Hiring Team,",
  "body": [
    "Paragraph 1 (3-4 sentences): Open with a specific hook about THIS company/role — reference something concrete from the JD. State which role you're applying for and the single strongest reason you're a fit.",
    "Paragraph 2 (4-5 sentences): Walk through 2-3 specific accomplishments from the candidate's actual experience that directly map to the JD's requirements. Include metrics where the profile provides them. Use 'I' statements.",
    "Paragraph 3 (3-4 sentences): Connect a specific skill or project from the profile to a responsibility in the JD. Show you've read the job description.",
    "Paragraph 4 (2-3 sentences): Reiterate interest, mention availability for a conversation, and thank them."
  ],
  "closing": "Sincerely,"
}}

HARD RULES:
- Every claim must trace back to the candidate profile. Do NOT fabricate.
- Name the company and role naturally in the body — not just the greeting.
- No generic filler ("I am a hardworking team player"). Every sentence must be specific.
- Output ONLY the JSON object. No markdown fences."""


def _parse_json(text: str, doc_type: str) -> Optional[dict]:
    """Try direct parse, then code-fence extraction, then brace extraction."""
    for candidate in _json_candidates(text):
        try:
            parsed = json.loads(candidate)
            logger.info(f"Parsed {doc_type} JSON")
            return parsed
        except (json.JSONDecodeError, TypeError):
            continue
    logger.warning(f"Could not parse {doc_type} JSON — using fallback. Raw: {text[:300]}")
    return None


def _json_candidates(text: str):
    yield text
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        yield m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        yield text[start : end + 1]


def _fallback_resume(profile: UserProfile) -> dict:
    skills = list(profile.skills)
    if profile.certifications:
        skills.insert(0, "Certifications: " + ", ".join(profile.certifications))
    return {
        "education": [str(e) for e in profile.education],
        "skills": skills,
        "experience": [str(e) for e in profile.experience],
        "projects": [str(p) for p in profile.projects],
    }


def _fallback_cover() -> dict:
    return {"greeting": "Dear Hiring Manager,", "body": [], "closing": "Sincerely,"}


# ── Plain-text variants (used by the CLI flow) ───────────────

def generate_documents_text(job: Job, profile: UserProfile) -> tuple[str, str]:
    """Return (resume_markdown, cover_letter_markdown)."""
    try:
        resume = client().generate(
            f"""You are a professional resume writer. Create a tailored resume.

CANDIDATE PROFILE:
{profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Create a professional resume in Markdown format. Keep it concise (1 page) and focus on relevant qualifications.""",
            max_tokens=1500, temperature=0.3,
        )
        cover = client().generate(
            f"""You are a professional cover letter writer.

CANDIDATE PROFILE:
{profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Write a professional cover letter (3-4 paragraphs) in Markdown format.""",
            max_tokens=1000, temperature=0.4,
        )
        return resume, cover
    except Exception as e:
        logger.error(f"Text doc generation failed for {job.title}: {e}")
        return "", ""

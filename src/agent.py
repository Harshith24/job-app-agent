"""Agents — CLI one-shot/scheduled runs, plus a background multi-user runner.

The CLI flow is driven by `run_cycle()` (reads config/profile.md and
config/job-criteria.md, writes markdown to ./output). The API flow uses
`AgentRunner` to periodically search, score, and persist jobs per user."""

import csv
import json
import logging
import re
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src import db, jobs, llm
from src.config import settings
from src.models import Job, JobApplication, JobSearchCriteria, UserProfile

logger = logging.getLogger(__name__)


# ── Health ───────────────────────────────────────────────────

def health_check() -> dict:
    status = {"overall": True, "services": {}}

    try:
        ollama_ok = llm.health_check()
        status["services"]["ollama"] = {"healthy": ollama_ok, "status": "OK" if ollama_ok else "UNHEALTHY"}
        status["overall"] &= ollama_ok
    except Exception as e:
        status["services"]["ollama"] = {"healthy": False, "status": f"ERROR: {e}"}
        status["overall"] = False

    fs_ok = True
    try:
        settings.config_path.exists() and settings.output_path.exists()
    except Exception:
        fs_ok = False
    status["services"]["filesystem"] = {"healthy": fs_ok, "status": "OK" if fs_ok else "ERROR"}
    status["overall"] &= fs_ok

    return status


# ══════════════════════════════════════════════════════════════
# CLI flow (reads local markdown config, writes local files)
# ══════════════════════════════════════════════════════════════

def run_cycle() -> Optional[str]:
    """Run one full search→rank→generate→write cycle. Returns output dir."""
    criteria = _load_criteria()
    profile = _load_profile()
    if not criteria or not profile:
        logger.error("Failed to load criteria or profile")
        return None

    found = jobs.search_jobs(criteria)
    if not found:
        logger.warning("No jobs found")
        return None

    top = llm.rank_jobs(found, criteria.keywords, settings.top_n_jobs)
    applications = [_make_application(job, profile) for job in top]

    output_dir = _write_applications(applications)
    logger.info(f"Cycle complete — output in {output_dir}")
    return str(output_dir)


def _load_criteria() -> Optional[JobSearchCriteria]:
    path = settings.config_path / "job-criteria.md"
    if not path.exists():
        logger.error(f"Criteria file not found: {path}")
        return None
    return JobSearchCriteria.from_markdown(path.read_text(encoding="utf-8"))


def _load_profile() -> Optional[UserProfile]:
    path = settings.config_path / "profile.md"
    if not path.exists():
        logger.error(f"Profile file not found: {path}")
        return None
    return UserProfile.from_markdown(path.read_text(encoding="utf-8"))


def _make_application(job: Job, profile: UserProfile) -> JobApplication:
    logger.info(f"Generating application for: {job.title} @ {job.company}")
    try:
        resume, cover = llm.generate_documents_text(job, profile)
    except Exception as e:
        logger.error(f"Doc gen failed for {job.title}: {e}")
        resume = "# Error generating resume\n"
        cover = "# Error generating cover letter\n"
    return JobApplication(job=job, resume_text=resume, cover_letter_text=cover)


def _write_applications(applications: list[JobApplication]) -> Path:
    output_dir = settings.output_path / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "job-list.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Company", "Location", "URL", "Resume File", "Cover File"])
        writer.writeheader()
        for app in applications:
            resume_name = _filename(app.job, "resume")
            cover_name = _filename(app.job, "cover")

            writer.writerow({
                "Title": app.job.title, "Company": app.job.company,
                "Location": app.job.location, "URL": app.job.url,
                "Resume File": resume_name, "Cover File": cover_name,
            })

            (output_dir / resume_name).write_text(app.resume_text, encoding="utf-8")
            (output_dir / cover_name).write_text(app.cover_letter_text, encoding="utf-8")

    logger.info(f"Wrote {len(applications)} applications to {output_dir}")
    return output_dir


def _filename(job: Job, doc_type: str) -> str:
    safe = lambda text: re.sub(r"[\s_-]+", "_", re.sub(r'[<>:"/\\|?*]', "_", text)).strip("_")[:50]
    return f"{doc_type}-{safe(job.company)}-{safe(job.title)}.md"


def cleanup_old_outputs(days_to_keep: int = 30):
    cutoff = datetime.now().timestamp() - days_to_keep * 86400
    try:
        for item in settings.output_path.iterdir():
            if not item.is_dir():
                continue
            try:
                datetime.strptime(item.name, "%Y-%m-%d")
            except ValueError:
                continue
            if item.stat().st_mtime < cutoff:
                shutil.rmtree(item)
                logger.info(f"Cleaned up old output: {item}")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


# ══════════════════════════════════════════════════════════════
# Background runner (multi-user, driven from the API)
# ══════════════════════════════════════════════════════════════

class AgentRunner:
    """One background thread that periodically runs a cycle for every user."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._running_for: dict[str, bool] = {}

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="agent-runner")
        self._thread.start()
        logger.info("Agent started")

    def stop(self):
        if self.running:
            self._stop.set()
            logger.info("Agent stop requested")

    def status(self) -> dict:
        return {
            "running": self.running,
            "interval_minutes": settings.agent_interval_minutes,
            "relevance_threshold": settings.relevance_threshold,
        }

    def run_once_for_user(self, user_id: str):
        """Trigger a one-off cycle for one user (API-triggered search)."""
        threading.Thread(
            target=self._run_for_user, args=(user_id,), daemon=True,
            name=f"agent-{user_id[:8]}",
        ).start()

    def _loop(self):
        interval = settings.agent_interval_minutes * 60
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Agent tick error: {e}")
            self._stop.wait(timeout=interval)
        logger.info("Agent loop stopped")

    def _tick(self):
        rows = db.get_all_criteria()
        logger.info(f"Agent tick — {len(rows)} users with criteria")
        for row in rows:
            if self._stop.is_set():
                break
            user_id = row.get("user_id")
            if user_id:
                self._run_for_user(user_id)

    def _run_for_user(self, user_id: str):
        if self._running_for.get(user_id):
            logger.info(f"Already running for user {user_id[:8]}")
            return
        self._running_for[user_id] = True

        run = db.insert_agent_run(user_id, {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        run_id = run.get("id")

        found_count, stored_count, error = 0, 0, None
        try:
            criteria_row = db.get_criteria(user_id)
            profile_row = db.get_profile(user_id)
            if not criteria_row or not profile_row:
                logger.warning(f"User {user_id[:8]} missing criteria/profile — skipping")
                return

            criteria = _criteria_from_row(criteria_row)
            profile = _profile_from_row(profile_row)

            raw_jobs = jobs.search_jobs(criteria)
            found_count = len(raw_jobs)
            logger.info(f"User {user_id[:8]}: found {found_count} raw jobs")

            for job in raw_jobs:
                if self._stop.is_set():
                    break
                if db.job_exists(user_id, job.title, job.company, job.url):
                    continue

                score = llm.score_relevance(job, profile)
                logger.info(f"  {job.title} @ {job.company} => {score}")
                if score < settings.relevance_threshold:
                    continue

                try:
                    resume_data, cover_data = llm.generate_documents(job, profile)
                except Exception as e:
                    logger.error(f"Doc gen failed for {job.title}: {e}")
                    resume_data, cover_data = {}, {}

                db.upsert_job(user_id, {
                    "title": job.title, "company": job.company,
                    "location": job.location, "description": job.description,
                    "url": job.url, "posted_date": job.posted_date,
                    "salary_range": job.salary_range, "job_type": job.job_type,
                    "source": job.source, "added_by": "agent",
                    "relevance_score": score,
                    "resume_text": json.dumps(resume_data) if resume_data else None,
                    "cover_letter_text": json.dumps(cover_data) if cover_data else None,
                })
                stored_count += 1
                logger.info(f"  Stored: {job.title} @ {job.company} (score={score})")

        except Exception as e:
            logger.error(f"Agent run failed for user {user_id[:8]}: {e}")
            error = str(e)[:500]
        finally:
            self._running_for[user_id] = False
            if run_id:
                db.update_agent_run(run_id, {
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed" if error else "completed",
                    "jobs_found": found_count,
                    "jobs_stored": stored_count,
                    "error": error,
                })


_runner: Optional[AgentRunner] = None


def runner() -> AgentRunner:
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


# ── Row → model helpers (kept here since they're agent-internal) ─

def _criteria_from_row(row: dict) -> JobSearchCriteria:
    return JobSearchCriteria(
        keywords=row.get("keywords", []),
        locations=row.get("locations", []),
        experience_levels=row.get("experience_levels", []),
        job_types=row.get("job_types", []),
        exclude_terms=row.get("exclude_terms", []),
    )


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

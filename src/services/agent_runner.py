"""Background agent that periodically searches for jobs, scores them, and
stores high-relevance matches with generated resume/cover-letter PDFs."""

import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from src.config.settings import config
from src.db import supabase_client as db
from src.models.job import Job, JobSearchCriteria, UserProfile
from src.services.job_search import JobSearchService
from src.services.ollama import OllamaClient, DocumentGenerator
from src.services.relevance import RelevanceScorer, RELEVANCE_THRESHOLD

logger = logging.getLogger(__name__)


class AgentRunner:
    """Manages the background search loop (one thread, all users)."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._interval = config.app.agent_interval_minutes * 60
        self._running_for: dict[str, bool] = {}

        self._search_svc = JobSearchService()
        ollama = OllamaClient(config.app.ollama_url, config.app.ollama_model)
        self._scorer = RelevanceScorer(ollama)
        self._doc_gen = DocumentGenerator(ollama)

    # ── public API ────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            logger.info("Agent already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="agent-runner")
        self._thread.start()
        logger.info("Agent started")

    def stop(self):
        if not self.running:
            return
        self._stop_event.set()
        logger.info("Agent stop requested")

    def status(self) -> dict:
        return {
            "running": self.running,
            "interval_minutes": config.app.agent_interval_minutes,
            "relevance_threshold": RELEVANCE_THRESHOLD,
        }

    def run_once_for_user(self, user_id: str):
        """Trigger a single search cycle for one user (called from API)."""
        threading.Thread(
            target=self._run_for_user,
            args=(user_id,),
            daemon=True,
            name=f"agent-{user_id[:8]}",
        ).start()

    # ── internal loop ─────────────────────────────────────────

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error(f"Agent tick error: {e}")
            self._stop_event.wait(timeout=self._interval)
        logger.info("Agent loop stopped")

    def _tick(self):
        """Run one cycle for every user that has search criteria."""
        rows = db.get_all_users_with_criteria()
        logger.info(f"Agent tick — {len(rows)} users with criteria")
        for row in rows:
            if self._stop_event.is_set():
                break
            user_id = row.get("user_id")
            if not user_id:
                continue
            self._run_for_user(user_id)

    def _run_for_user(self, user_id: str):
        if self._running_for.get(user_id):
            logger.info(f"Agent already running for user {user_id[:8]}")
            return
        self._running_for[user_id] = True

        run_row = db.insert_agent_run(user_id, {
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        run_id = run_row.get("id")

        jobs_found = 0
        jobs_stored = 0
        error_msg = None

        try:
            criteria_row = db.get_criteria(user_id)
            profile_row = db.get_profile(user_id)
            if not criteria_row or not profile_row:
                logger.warning(f"User {user_id[:8]} missing criteria or profile — skipping")
                return

            criteria = JobSearchCriteria(
                keywords=criteria_row.get("keywords", []),
                locations=criteria_row.get("locations", []),
                experience_levels=criteria_row.get("experience_levels", []),
                job_types=criteria_row.get("job_types", []),
                exclude_terms=criteria_row.get("exclude_terms", []),
            )
            profile = UserProfile(
                name=profile_row.get("name"),
                email=profile_row.get("email"),
                phone=profile_row.get("phone"),
                linkedin=profile_row.get("linkedin"),
                location=profile_row.get("location"),
                experience=profile_row.get("experience", []),
                projects=profile_row.get("projects", []),
                certifications=profile_row.get("certifications", []),
                education=profile_row.get("education", []),
                skills=profile_row.get("skills", []),
            )

            # 1) search
            raw_jobs = self._search_svc.search_jobs(criteria)
            jobs_found = len(raw_jobs)
            logger.info(f"User {user_id[:8]}: found {jobs_found} raw jobs")

            for job in raw_jobs:
                if self._stop_event.is_set():
                    break

                # 2) dedup
                if db.job_exists(user_id, job.title, job.company, job.url):
                    continue

                # 3) relevance scoring
                score = self._scorer.score(job, profile)
                logger.info(f"  {job.title} @ {job.company} => score {score}")

                if score < RELEVANCE_THRESHOLD:
                    continue

                # 4) generate docs
                try:
                    resume_data, cover_data = self._doc_gen.generate_structured_application(job, profile)
                except Exception as e:
                    logger.error(f"Doc gen failed for {job.title}: {e}")
                    resume_data, cover_data = {}, {}

                # 5) store
                db.upsert_job(user_id, {
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "description": job.description,
                    "url": job.url,
                    "posted_date": job.posted_date,
                    "salary_range": job.salary_range,
                    "job_type": job.job_type,
                    "source": job.source,
                    "added_by": "agent",
                    "relevance_score": score,
                    "resume_text": json.dumps(resume_data) if resume_data else None,
                    "cover_letter_text": json.dumps(cover_data) if cover_data else None,
                })
                jobs_stored += 1
                logger.info(f"  Stored: {job.title} @ {job.company} (score={score})")

        except Exception as e:
            logger.error(f"Agent run failed for user {user_id[:8]}: {e}")
            error_msg = str(e)[:500]
        finally:
            self._running_for[user_id] = False
            if run_id:
                try:
                    db.get_service_client().table("agent_runs").update({
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                        "status": "failed" if error_msg else "completed",
                        "jobs_found": jobs_found,
                        "jobs_stored": jobs_stored,
                        "error": error_msg,
                    }).eq("id", run_id).execute()
                except Exception:
                    pass


# Module-level singleton
_runner: Optional[AgentRunner] = None


def get_runner() -> AgentRunner:
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner

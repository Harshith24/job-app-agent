"""Job search via python-jobspy (LinkedIn scraping)."""

import logging
import math
from typing import Optional

from src.models import Job, JobSearchCriteria

logger = logging.getLogger(__name__)

_JOB_TYPE_MAP = {
    "full-time": "fulltime", "fulltime": "fulltime",
    "part-time": "parttime", "parttime": "parttime",
    "contract": "contract", "internship": "internship",
}


def search_jobs(criteria: JobSearchCriteria) -> list[Job]:
    """Search LinkedIn (via JobSpy). Returns deduplicated Jobs."""
    try:
        jobs = _scrape(criteria)
    except Exception as e:
        logger.warning(f"JobSpy search failed: {e}")
        return []

    unique = _deduplicate(jobs)
    logger.info(f"Found {len(unique)} unique jobs")
    return unique


def _scrape(criteria: JobSearchCriteria) -> list[Job]:
    from jobspy import scrape_jobs  # heavy import — keep local

    query = " ".join(criteria.keywords[:3]) if criteria.keywords else "software engineer"
    location = _pick_location(criteria.locations)
    is_remote = any("remote" in loc.lower() for loc in criteria.locations)
    google_term = f"{query} remote jobs" if is_remote else (f"{query} jobs in {location}" if location else f"{query} jobs")

    logger.info(f"JobSpy — query='{query}', location='{location}', remote={is_remote}")

    df = scrape_jobs(
        site_name=["linkedin"],
        search_term=query,
        google_search_term=google_term,
        location=location,
        is_remote=is_remote,
        job_type=_pick_job_type(criteria.job_types),
        results_wanted=15,
        hours_old=72,
        verbose=0,
    )

    if df is None or df.empty:
        return []

    exclude = [e.lower() for e in criteria.exclude_terms]
    jobs: list[Job] = []

    for _, row in df.iterrows():
        title = _clean(row.get("title"))
        url = _clean(row.get("job_url"))
        if not title or not url:
            continue

        desc = _clean(row.get("description"))
        searchable = f"{title} {desc[:500]}".lower()
        if exclude and any(term in searchable for term in exclude):
            continue

        city, state = _clean(row.get("city")), _clean(row.get("state"))
        loc = ", ".join(p for p in [city, state] if p) or _clean(row.get("location"))
        if _clean(row.get("is_remote")).lower() in ("true", "1"):
            loc = f"{loc} (Remote)".strip(" ()")

        jobs.append(Job(
            title=title,
            company=_clean(row.get("company")),
            location=loc,
            description=desc[:3000],
            url=url,
            posted_date=_clean(row.get("date_posted")),
            salary_range=_format_salary(row.get("min_amount"), row.get("max_amount")),
            job_type=_clean(row.get("job_type")),
            source=_clean(row.get("site")).title() or "JobSpy",
        ))

    return jobs


def _pick_location(locations: list[str]) -> str:
    non_remote = [l for l in locations if "remote" not in l.lower()]
    if non_remote:
        return non_remote[0]
    return locations[0] if locations else "United States"


def _pick_job_type(job_types: list[str]) -> Optional[str]:
    for jt in job_types:
        mapped = _JOB_TYPE_MAP.get(jt.lower().replace(" ", "-"))
        if mapped:
            return mapped
    return None


def _format_salary(min_s, max_s) -> Optional[str]:
    def ok(v):
        return v is not None and not (isinstance(v, float) and math.isnan(v))
    try:
        if ok(min_s) and ok(max_s):
            return f"${int(min_s):,} - ${int(max_s):,}"
        if ok(min_s):
            return f"${int(min_s):,}+"
        if ok(max_s):
            return f"Up to ${int(max_s):,}"
    except (TypeError, ValueError):
        pass
    return None


def _clean(val) -> str:
    """Coerce a possibly-NaN pandas value into a trimmed string."""
    if val is None:
        return ""
    try:
        if isinstance(val, float) and math.isnan(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


def _deduplicate(jobs: list[Job]) -> list[Job]:
    seen, unique = set(), []
    for j in jobs:
        if j.unique_key not in seen:
            seen.add(j.unique_key)
            unique.append(j)
    return unique

"""Job search service — primary: python-jobspy (LinkedIn/Indeed/Glassdoor/ZipRecruiter/Google),
fallback: RemoteOK & Arbeitnow free JSON APIs."""

import re
import html
import logging
import requests
from typing import List, Optional

from src.config.settings import config
from src.models.job import Job

logger = logging.getLogger(__name__)


class JobSearchError(Exception):
    pass


def _safe_str(val) -> str:
    """Return a clean string from a possibly-NaN pandas value."""
    import math
    if val is None:
        return ""
    try:
        if math.isnan(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


class JobSearchService:
    """Unified job search across multiple sources."""

    def __init__(self):
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")

    def search_jobs(self, criteria) -> List[Job]:
        """For now, only fetch from LinkedIn via JobSpy so we can inspect results."""
        try:
            jobs = self._search_jobspy(criteria)
            unique = self._deduplicate(jobs)
            self.logger.info(f"LinkedIn (JobSpy) unique jobs: {len(unique)}")
            return unique
        except Exception as e:
            self.logger.warning(f"JobSpy (LinkedIn) search failed: {e}")
            return []

    # ── Primary: JobSpy ──────────────────────────────────────────────────────

    def _search_jobspy(self, criteria) -> List[Job]:
        """Scrape LinkedIn via python-jobspy (restricted to LinkedIn for debugging)."""
        from jobspy import scrape_jobs  # deferred import — heavy deps

        search_term = self._build_query(criteria)
        location = self._pick_location(criteria)
        is_remote = self._is_remote(criteria)
        job_type = self._map_job_type(criteria)

        # Google Jobs needs a richer natural-language query
        google_term = self._build_google_query(criteria)

        self.logger.info(
            f"JobSpy scraping — query='{search_term}', location='{location}', "
            f"remote={is_remote}, job_type={job_type}"
        )

        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=search_term,
            google_search_term=google_term,
            location=location,
            is_remote=is_remote,
            job_type=job_type,
            results_wanted=15,   # per site — keep low to avoid rate limiting
            hours_old=72,        # only recent postings
            verbose=0,
        )

        if df is None or df.empty:
            return []

        jobs: List[Job] = []
        exclude_lower = [e.lower() for e in (criteria.exclude_terms or [])]

        for _, row in df.iterrows():
            title = _safe_str(row.get("title"))
            company = _safe_str(row.get("company"))
            desc = _safe_str(row.get("description"))
            url = _safe_str(row.get("job_url"))

            # Location — combine city/state or fall back to column
            city = _safe_str(row.get("city"))
            state = _safe_str(row.get("state"))
            loc = ", ".join(filter(None, [city, state])) or _safe_str(row.get("location", ""))
            if _safe_str(row.get("is_remote")) in ("True", "true", "1"):
                loc = f"{loc} (Remote)".strip(" ()")

            # Salary
            min_s = row.get("min_amount")
            max_s = row.get("max_amount")
            salary = self._format_salary(min_s, max_s)

            date_posted = _safe_str(row.get("date_posted"))
            job_type_out = _safe_str(row.get("job_type"))
            source = _safe_str(row.get("site")).title() or "JobSpy"

            # Exclude-term filter
            searchable = f"{title} {desc[:500]}".lower()
            if exclude_lower and any(e in searchable for e in exclude_lower):
                continue

            if not title or not url:
                continue

            jobs.append(Job(
                title=title,
                company=company,
                location=loc,
                description=desc[:3000],
                url=url,
                posted_date=date_posted,
                salary_range=salary,
                job_type=job_type_out,
                source=source,
            ))

        return jobs

    # ── Supplemental: RemoteOK ────────────────────────────────────────────────

    def _search_remoteok(self, criteria) -> List[Job]:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": "JobSearchAgent/2.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data and "legal" in str(data[0]):
            data = data[1:]

        keywords_lower = [k.lower() for k in (criteria.keywords or [])]
        exclude_lower = [e.lower() for e in (criteria.exclude_terms or [])]

        jobs: List[Job] = []
        for item in data:
            title = (item.get("position") or "").strip()
            company = (item.get("company") or "").strip()
            desc = html.unescape(item.get("description") or "")
            desc = re.sub(r"<[^>]+>", " ", desc)
            url = item.get("url") or item.get("apply_url") or ""
            location = item.get("location") or "Remote"
            tags = [t.lower() for t in (item.get("tags") or [])]

            searchable = f"{title} {' '.join(tags)} {desc[:500]}".lower()
            if exclude_lower and any(e in searchable for e in exclude_lower):
                continue
            if keywords_lower and not any(k in searchable for k in keywords_lower):
                continue

            jobs.append(Job(
                title=title,
                company=company,
                location=location,
                description=desc[:3000],
                url=url,
                posted_date=item.get("date", ""),
                salary_range=self._format_salary(item.get("salary_min"), item.get("salary_max")),
                job_type="full-time",
                source="RemoteOK",
            ))
        return jobs

    # ── Supplemental: Arbeitnow ───────────────────────────────────────────────

    def _search_arbeitnow(self, criteria) -> List[Job]:
        resp = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json().get("data", [])

        keywords_lower = [k.lower() for k in (criteria.keywords or [])]
        exclude_lower = [e.lower() for e in (criteria.exclude_terms or [])]

        jobs: List[Job] = []
        for item in items:
            title = (item.get("title") or "").strip()
            company = (item.get("company_name") or "").strip()
            desc = html.unescape(item.get("description") or "")
            desc = re.sub(r"<[^>]+>", " ", desc)
            url = item.get("url") or ""
            location = item.get("location") or ""
            tags = [t.lower() for t in (item.get("tags") or [])]

            searchable = f"{title} {' '.join(tags)} {desc[:500]}".lower()
            if exclude_lower and any(e in searchable for e in exclude_lower):
                continue
            if keywords_lower and not any(k in searchable for k in keywords_lower):
                continue

            if item.get("remote"):
                location = f"{location} (Remote)".strip(" ()") if location else "Remote"

            jobs.append(Job(
                title=title,
                company=company,
                location=location,
                description=desc[:3000],
                url=url,
                posted_date=item.get("created_at", ""),
                job_type="full-time",
                source="Arbeitnow",
            ))
        return jobs

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_query(self, criteria) -> str:
        parts = list(criteria.keywords[:3]) if criteria.keywords else ["software engineer"]
        return " ".join(parts)

    def _build_google_query(self, criteria) -> str:
        """Google Jobs needs a natural-language query string."""
        query = self._build_query(criteria)
        loc = self._pick_location(criteria)
        if self._is_remote(criteria):
            return f"{query} remote jobs"
        return f"{query} jobs in {loc}" if loc else f"{query} jobs"

    def _pick_location(self, criteria) -> str:
        """Return the best single location string for JobSpy."""
        locations = criteria.locations or []
        non_remote = [l for l in locations if "remote" not in l.lower()]
        return non_remote[0] if non_remote else (locations[0] if locations else "United States")

    def _is_remote(self, criteria) -> bool:
        return any("remote" in loc.lower() for loc in (criteria.locations or []))

    def _map_job_type(self, criteria) -> Optional[str]:
        """Map our job_types to JobSpy's accepted values."""
        mapping = {
            "full-time": "fulltime",
            "fulltime": "fulltime",
            "part-time": "parttime",
            "parttime": "parttime",
            "contract": "contract",
            "internship": "internship",
        }
        for jt in (criteria.job_types or []):
            mapped = mapping.get(jt.lower().replace(" ", "-"))
            if mapped:
                return mapped
        return None  # None = no filter

    def _format_salary(self, min_s, max_s) -> Optional[str]:
        try:
            import math
            min_ok = min_s is not None and not (isinstance(min_s, float) and math.isnan(min_s))
            max_ok = max_s is not None and not (isinstance(max_s, float) and math.isnan(max_s))
            if min_ok and max_ok:
                return f"${int(min_s):,} - ${int(max_s):,}"
            if min_ok:
                return f"${int(min_s):,}+"
            if max_ok:
                return f"Up to ${int(max_s):,}"
        except (TypeError, ValueError):
            pass
        return None

    def _deduplicate(self, jobs: List[Job]) -> List[Job]:
        seen: set = set()
        unique: List[Job] = []
        for job in jobs:
            key = job.unique_key
            if key not in seen:
                seen.add(key)
                unique.append(job)
        return unique

"""Job search service integrations"""

import requests
import logging
import re
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config.settings import config
from src.models.job import Job

logger = logging.getLogger(__name__)

class JobSearchError(Exception):
    """Job search service error"""
    pass

class JobSearchService:
    """Unified job search across multiple APIs"""

    def __init__(self):
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.jsearch_available = bool(config.app.jsearch_api_key)
        self.adzuna_available = bool(config.app.adzuna_app_id and config.app.adzuna_app_key)

        if not (self.jsearch_available or self.adzuna_available):
            self.logger.warning("No job search APIs configured")

    def search_jobs(self, criteria) -> List[Job]:
        """Search for jobs across all available sources"""
        all_jobs = []

        if self.jsearch_available:
            try:
                jobs = self._search_jsearch(criteria)
                all_jobs.extend(jobs)
                self.logger.info(f"JSearch found {len(jobs)} jobs")
            except Exception as e:
                self.logger.error(f"JSearch search failed: {e}")

        if self.adzuna_available:
            try:
                jobs = self._search_adzuna(criteria)
                all_jobs.extend(jobs)
                self.logger.info(f"Adzuna found {len(jobs)} jobs")
            except Exception as e:
                self.logger.error(f"Adzuna search failed: {e}")

        # Deduplicate jobs
        unique_jobs = self._deduplicate_jobs(all_jobs)
        self.logger.info(f"Total unique jobs found: {len(unique_jobs)}")

        return unique_jobs

    @retry(
        stop=stop_after_attempt(config.app.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _search_jsearch(self, criteria) -> List[Job]:
        """Search using JSearch API"""
        search_query = self._build_search_query(criteria)

        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": config.app.jsearch_api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        params = {
            "query": search_query,
            "num_pages": "1",
            "country": "US"
        }

        response = requests.get(url, headers=headers, params=params, timeout=config.app.request_timeout)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for item in data.get('data', []):
            job = Job(
                title=item.get('job_title', ''),
                company=item.get('employer_name', ''),
                location=f"{item.get('job_city', '')}, {item.get('job_state', '')}".strip(', '),
                description=item.get('job_description', ''),
                url=item.get('job_apply_link', ''),
                posted_date=item.get('job_posted_at_datetime_utc', ''),
                salary_range=self._format_salary_range(
                    item.get('job_min_salary'),
                    item.get('job_max_salary')
                ),
                job_type=item.get('job_employment_type', ''),
                source='JSearch'
            )
            jobs.append(job)

        return jobs

    @retry(
        stop=stop_after_attempt(config.app.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _search_adzuna(self, criteria) -> List[Job]:
        """Search using Adzuna API"""
        search_query = self._build_search_query(criteria)

        url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
        params = {
            "app_id": config.app.adzuna_app_id,
            "app_key": config.app.adzuna_app_key,
            "what": search_query,
            "results_per_page": "50"
        }

        response = requests.get(url, params=params, timeout=config.app.request_timeout)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for item in data.get('results', []):
            job = Job(
                title=item.get('title', ''),
                company=item.get('company', {}).get('display_name', ''),
                location=item.get('location', {}).get('display_name', ''),
                description=item.get('description', ''),
                url=item.get('redirect_url', ''),
                posted_date=item.get('created', ''),
                salary_range=self._format_salary_range(
                    item.get('salary_min'),
                    item.get('salary_max')
                ),
                job_type=item.get('contract_type', ''),
                source='Adzuna'
            )
            jobs.append(job)

        return jobs

    def _build_search_query(self, criteria) -> str:
        """Build search query from criteria"""
        query_parts = []

        # Add keywords
        if criteria.keywords:
            query_parts.extend(criteria.keywords[:3])  # Limit to top 3 keywords

        # Add location preferences
        if criteria.locations:
            # Prioritize remote if mentioned
            if any('remote' in loc.lower() for loc in criteria.locations):
                query_parts.append('remote')

        # Join query parts
        query = ' '.join(query_parts)
        return query or 'software engineer'  # Default fallback

    def _format_salary_range(self, min_salary: Optional[str], max_salary: Optional[str]) -> Optional[str]:
        """Format salary range string"""
        if min_salary and max_salary:
            return f"${min_salary} - ${max_salary}"
        elif min_salary:
            return f"${min_salary}+"
        elif max_salary:
            return f"Up to ${max_salary}"
        return None

    def _deduplicate_jobs(self, jobs: List[Job]) -> List[Job]:
        """Remove duplicate jobs based on unique key"""
        seen = set()
        unique_jobs = []

        for job in jobs:
            key = job.unique_key
            if key not in seen:
                seen.add(key)
                unique_jobs.append(job)

        return unique_jobs
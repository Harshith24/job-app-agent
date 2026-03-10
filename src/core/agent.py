"""Core job search agent orchestration"""

import logging
from typing import List, Optional

from src.config.settings import config
from src.models.job import Job, JobApplication, JobSearchCriteria, UserProfile
from src.services.ollama import OllamaClient, JobRanker, DocumentGenerator
from src.services.job_search import JobSearchService
from src.services.output import OutputService

logger = logging.getLogger(__name__)

class JobSearchAgent:
    """Main job search agent orchestrator"""

    def __init__(self):
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize services
        self.ollama_client = OllamaClient(config.app.ollama_url, config.app.ollama_model)
        self.job_search = JobSearchService()
        self.job_ranker = JobRanker(self.ollama_client)
        self.doc_generator = DocumentGenerator(self.ollama_client)
        self.output_service = OutputService()

        # Cache for loaded data
        self._criteria: Optional[JobSearchCriteria] = None
        self._profile: Optional[UserProfile] = None

    def run_search_cycle(self) -> Optional[str]:
        """Run complete job search cycle"""
        try:
            self.logger.info("Starting job search cycle")

            # Load configuration
            criteria = self._load_criteria()
            profile = self._load_profile()

            if not criteria or not profile:
                self.logger.error("Failed to load search criteria or profile")
                return None

            # Search for jobs
            jobs = self.job_search.search_jobs(criteria)
            if not jobs:
                self.logger.warning("No jobs found")
                return None

            # Rank jobs
            top_jobs = self.job_ranker.rank_jobs(jobs, criteria.keywords, config.app.top_n_jobs)

            # Generate applications
            applications = self._generate_applications(top_jobs, profile)

            # Generate output
            output_dir = self.output_service.generate_output(applications)

            self.logger.info(f"Job search cycle completed. Output: {output_dir}")
            return output_dir

        except Exception as e:
            self.logger.error(f"Job search cycle failed: {e}")
            raise

    def _load_criteria(self) -> Optional[JobSearchCriteria]:
        """Load job search criteria"""
        if self._criteria:
            return self._criteria

        try:
            criteria_file = config.app.config_path / 'job-criteria.md'
            if not criteria_file.exists():
                self.logger.error(f"Job criteria file not found: {criteria_file}")
                return None

            content = criteria_file.read_text(encoding='utf-8')
            self._criteria = JobSearchCriteria.from_markdown(content)
            self.logger.info("Loaded job search criteria")
            return self._criteria

        except Exception as e:
            self.logger.error(f"Failed to load job criteria: {e}")
            return None

    def _load_profile(self) -> Optional[UserProfile]:
        """Load user profile"""
        if self._profile:
            return self._profile

        try:
            profile_file = config.app.config_path / 'profile.md'
            if not profile_file.exists():
                self.logger.error(f"Profile file not found: {profile_file}")
                return None

            content = profile_file.read_text(encoding='utf-8')
            self._profile = UserProfile.from_markdown(content)
            self.logger.info("Loaded user profile")
            return self._profile

        except Exception as e:
            self.logger.error(f"Failed to load user profile: {e}")
            return None

    def _generate_applications(self, jobs: List[Job], profile: UserProfile) -> List[JobApplication]:
        """Generate applications for top jobs"""
        applications = []

        for job in jobs:
            self.logger.info(f"Generating application for: {job.title} at {job.company}")

            try:
                resume_text, cover_text = self.doc_generator.generate_application(job, profile)

                application = JobApplication(
                    job=job,
                    resume_text=resume_text,
                    cover_letter_text=cover_text
                )
                applications.append(application)

            except Exception as e:
                self.logger.error(f"Failed to generate application for {job.title}: {e}")
                # Create application with empty documents rather than failing
                application = JobApplication(
                    job=job,
                    resume_text="# Error generating resume\n\nUnable to generate resume at this time.",
                    cover_letter_text="# Error generating cover letter\n\nUnable to generate cover letter at this time."
                )
                applications.append(application)

        return applications

    def health_check(self) -> dict:
        """Perform health check on all services"""
        health_status = {
            'overall': True,
            'services': {}
        }

        # Check Ollama
        try:
            ollama_healthy = self.ollama_client.health_check()
            health_status['services']['ollama'] = {
                'healthy': ollama_healthy,
                'status': 'OK' if ollama_healthy else 'UNHEALTHY'
            }
            if not ollama_healthy:
                health_status['overall'] = False
        except Exception as e:
            health_status['services']['ollama'] = {
                'healthy': False,
                'status': f'ERROR: {e}'
            }
            health_status['overall'] = False

        # Check job search APIs
        job_search_healthy = bool(config.app.jsearch_api_key or (config.app.adzuna_app_id and config.app.adzuna_app_key))
        health_status['services']['job_search'] = {
            'healthy': job_search_healthy,
            'status': 'OK' if job_search_healthy else 'NO API KEYS CONFIGURED'
        }
        if not job_search_healthy:
            health_status['overall'] = False

        # Check file system
        try:
            config.app.config_path.exists()
            config.app.output_path.exists()
            fs_healthy = True
        except Exception:
            fs_healthy = False

        health_status['services']['filesystem'] = {
            'healthy': fs_healthy,
            'status': 'OK' if fs_healthy else 'ERROR'
        }
        if not fs_healthy:
            health_status['overall'] = False

        return health_status
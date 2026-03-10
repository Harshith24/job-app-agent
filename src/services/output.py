"""Output generation and file management"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import List

from src.config.settings import config
from src.models.job import Job, JobApplication

logger = logging.getLogger(__name__)

class OutputService:
    """Handles output file generation and management"""

    def __init__(self):
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")

    def generate_output(self, applications: List[JobApplication]) -> str:
        """Generate output files for job applications"""
        # Create output directory for today
        today = datetime.now().strftime('%Y-%m-%d')
        output_dir = config.app.output_path / today
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate CSV job list
        csv_path = self._write_job_list_csv(applications, output_dir)

        # Generate individual application files
        for app in applications:
            self._write_application_files(app, output_dir)

        self.logger.info(f"Generated output for {len(applications)} applications in {output_dir}")
        return str(output_dir)

    def _write_job_list_csv(self, applications: List[JobApplication], output_dir: Path) -> Path:
        """Write job list CSV file"""
        csv_path = output_dir / 'job-list.csv'

        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Title', 'Company', 'Location', 'URL', 'Resume File', 'Cover File']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for app in applications:
                resume_file = self._get_application_filename(app.job, 'resume')
                cover_file = self._get_application_filename(app.job, 'cover')

                writer.writerow({
                    'Title': app.job.title,
                    'Company': app.job.company,
                    'Location': app.job.location,
                    'URL': app.job.url,
                    'Resume File': resume_file,
                    'Cover File': cover_file
                })

        self.logger.debug(f"Generated CSV: {csv_path}")
        return csv_path

    def _write_application_files(self, application: JobApplication, output_dir: Path):
        """Write resume and cover letter files for a job application"""
        resume_file = self._get_application_filename(application.job, 'resume')
        cover_file = self._get_application_filename(application.job, 'cover')

        # Write resume
        resume_path = output_dir / resume_file
        resume_path.write_text(application.resume_text, encoding='utf-8')

        # Write cover letter
        cover_path = output_dir / cover_file
        cover_path.write_text(application.cover_letter_text, encoding='utf-8')

        self.logger.debug(f"Generated application files for: {application.job.title}")

    def _get_application_filename(self, job: Job, doc_type: str) -> str:
        """Generate safe filename for application documents"""
        safe_title = self._safe_filename(job.title)
        safe_company = self._safe_filename(job.company)

        return f"{doc_type}-{safe_company}-{safe_title}.md"

    def _safe_filename(self, text: str) -> str:
        """Convert text to safe filename"""
        import re
        # Remove or replace unsafe characters
        safe = re.sub(r'[<>:"/\\|?*]', '_', text)
        # Remove multiple spaces/dashes
        safe = re.sub(r'[\s_-]+', '_', safe)
        # Limit length and strip
        return safe.strip('_')[:50]

    def cleanup_old_outputs(self, days_to_keep: int = 30):
        """Clean up old output directories"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

            for item in config.app.output_path.iterdir():
                if item.is_dir():
                    try:
                        # Check if directory name looks like a date
                        datetime.strptime(item.name, '%Y-%m-%d')
                        if item.stat().st_mtime < cutoff_date:
                            import shutil
                            shutil.rmtree(item)
                            self.logger.info(f"Cleaned up old output directory: {item}")
                    except ValueError:
                        # Not a date directory, skip
                        pass

        except Exception as e:
            self.logger.error(f"Failed to cleanup old outputs: {e}")
"""Ollama AI service integration"""

import requests
import time
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config.settings import config

logger = logging.getLogger(__name__)

class OllamaError(Exception):
    """Ollama service error"""
    pass

class OllamaClient:
    """Ollama API client with retry logic and error handling"""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")

    def health_check(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Ollama health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(config.app.max_retries),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((requests.RequestException, OllamaError))
    )
    def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Generate text using Ollama with retry logic"""
        try:
            start_time = time.time()

            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=config.app.request_timeout
            )

            response.raise_for_status()
            result = response.json()
            response_text = result.get('response', '').strip()

            duration = time.time() - start_time
            self.logger.info(".2f")

            if not response_text:
                raise OllamaError("Empty response from Ollama")

            return response_text

        except requests.Timeout:
            self.logger.error(f"Ollama request timeout for model {self.model}")
            raise OllamaError("Request timeout")
        except requests.RequestException as e:
            self.logger.error(f"Ollama request failed: {e}")
            raise OllamaError(f"Request failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected Ollama error: {e}")
            raise OllamaError(f"Unexpected error: {e}")

class JobRanker:
    """Job ranking using Ollama AI"""

    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")

    def rank_jobs(self, jobs: list, criteria: str, top_n: int = 10) -> list:
        """Rank jobs by relevance to search criteria"""
        if not jobs:
            return []

        try:
            # Try AI-powered ranking first
            ranked_jobs = self._ollama_ranking(jobs, criteria, top_n)
            if ranked_jobs:
                self.logger.info(f"AI ranked {len(ranked_jobs)} jobs")
                return ranked_jobs[:top_n]
        except Exception as e:
            self.logger.warning(f"Ollama ranking failed, falling back to keyword ranking: {e}")

        # Fallback to keyword-based ranking
        scores = self._keyword_ranking(jobs, keywords)
        sorted_jobs = sorted(jobs, key=lambda j: scores.get(j, 0), reverse=True)
        ranked_jobs = sorted_jobs[:top_n]
        self.logger.info(f"Keyword ranked {len(ranked_jobs)} jobs")
        return ranked_jobs

    def _ollama_ranking(self, jobs: list, criteria: str, top_n: int) -> list:
        """Use Ollama to intelligently rank jobs"""
        job_descriptions = []
        for i, job in enumerate(jobs):
            desc = f"{i+1}. {job.title} at {job.company} - {job.location}"
            desc += f" - {job.description[:300]}..." if job.description else ""
            job_descriptions.append(desc)

        prompt = f"""
You are a job search assistant. Based on the following job search criteria, rank these jobs by relevance.

CRITERIA:
{criteria}

JOBS TO RANK:
{chr(10).join(job_descriptions)}

Please respond with a ranked list of job indices (1-based) in order of relevance, separated by commas.
Most relevant first. Only return the indices, no other text.
"""

        response = self.ollama.generate(prompt, max_tokens=500, temperature=0.1)
        if not response:
            return []

        try:
            indices = []
            for part in response.split(','):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(jobs):
                        indices.append(idx)

            # Remove duplicates while preserving order
            seen = set()
            unique_indices = []
            for idx in indices:
                if idx not in seen:
                    seen.add(idx)
                    unique_indices.append(idx)

            return [jobs[idx] for idx in unique_indices]

        except (ValueError, IndexError) as e:
            self.logger.warning(f"Failed to parse Ollama ranking response: {e}")
            return []

    def _keyword_ranking(self, jobs: list, keywords: list[str]) -> dict:
        """Fallback keyword-based ranking"""
        # Score jobs
        scores = {}
        for job in jobs:
            text = f"{job.title} {job.description} {job.company}".lower()
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            scores[job] = score

        return scores

class DocumentGenerator:
    """Resume and cover letter generation using Ollama"""

    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client
        self.logger = config.get_logger(f"{__name__}.{self.__class__.__name__}")

    def generate_application(self, job, user_profile) -> tuple[str, str]:
        """Generate resume and cover letter for a job"""
        try:
            resume = self._generate_resume(job, user_profile)
            cover_letter = self._generate_cover_letter(job, user_profile)

            self.logger.info(f"Generated documents for: {job.title} at {job.company}")
            return resume, cover_letter

        except Exception as e:
            self.logger.error(f"Failed to generate documents for {job.title}: {e}")
            return "", ""

    def _generate_resume(self, job, user_profile) -> str:
        """Generate tailored resume"""
        prompt = f"""
You are a professional resume writer. Create a tailored resume based on the candidate's profile and the specific job requirements.

CANDIDATE PROFILE:
{user_profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Create a professional resume in Markdown format that highlights relevant experience, skills, and achievements that match this job. Keep it concise (1 page worth) and focus on the most relevant qualifications.
"""

        return self.ollama.generate(prompt, max_tokens=1500, temperature=0.3)

    def _generate_cover_letter(self, job, user_profile) -> str:
        """Generate tailored cover letter"""
        prompt = f"""
You are a professional cover letter writer. Create a compelling cover letter based on the candidate's profile and the specific job.

CANDIDATE PROFILE:
{user_profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Write a professional cover letter in Markdown format that explains why the candidate is interested in this role and company, and how their experience makes them a great fit. Keep it to 3-4 paragraphs.
"""

        return self.ollama.generate(prompt, max_tokens=1000, temperature=0.4)
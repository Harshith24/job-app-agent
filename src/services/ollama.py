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
            self.logger.info(f"Ollama response in {duration:.2f}s")

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
        keywords_list = criteria if isinstance(criteria, list) else [criteria]
        scores = self._keyword_ranking(jobs, keywords_list)
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

        criteria_str = ", ".join(criteria) if isinstance(criteria, list) else str(criteria)
        prompt = f"""
You are a job search assistant. Based on the following job search criteria, rank these jobs by relevance.

CRITERIA:
{criteria_str}

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

    # ── Legacy text-based generation (used by CLI agent) ──

    def generate_application(self, job, user_profile) -> tuple[str, str]:
        """Generate resume and cover letter as plain text."""
        try:
            resume = self._generate_resume_text(job, user_profile)
            cover_letter = self._generate_cover_letter_text(job, user_profile)
            self.logger.info(f"Generated documents for: {job.title} at {job.company}")
            return resume, cover_letter
        except Exception as e:
            self.logger.error(f"Failed to generate documents for {job.title}: {e}")
            return "", ""

    # ── Structured generation (used by API for PDF) ──

    def generate_structured_application(self, job, user_profile) -> tuple[dict, dict]:
        """Generate resume and cover letter as structured dicts for PDF."""
        try:
            resume_data = self._generate_resume_json(job, user_profile)
        except Exception as e:
            self.logger.error(f"Resume generation failed for {job.title}: {e}")
            resume_data = self._fallback_resume(user_profile)

        try:
            cover_data = self._generate_cover_letter_json(job, user_profile)
        except Exception as e:
            self.logger.error(f"Cover letter generation failed for {job.title}: {e}")
            cover_data = self._fallback_cover()

        self.logger.info(f"Generated structured docs for: {job.title} at {job.company}")
        return resume_data, cover_data

    # ── Resume (structured JSON) ──

    def _generate_resume_json(self, job, user_profile) -> dict:
        prompt = f"""You are a professional resume writer. Create a tailored 1-page resume.

CANDIDATE PROFILE:
{user_profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Output ONLY a valid JSON object (no markdown fences, no commentary) with this structure:
{{
  "summary": "2-3 sentence professional summary tailored to this role",
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Start - End",
      "bullets": ["Achievement or responsibility 1", "Achievement 2"]
    }}
  ],
  "education": [
    {{
      "degree": "Degree Name",
      "school": "School Name",
      "year": "Year"
    }}
  ],
  "skills": ["Skill 1", "Skill 2", "Skill 3"],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Brief description"
    }}
  ],
  "certifications": ["Certification 1"]
}}

RULES:
- Use ONLY the candidate's actual data — do NOT fabricate experience or credentials
- Tailor bullets and summary to emphasise qualifications relevant to THIS job
- Keep content concise — it must fit on one printed page
- Output valid JSON only"""

        raw = self.ollama.generate(prompt, max_tokens=2000, temperature=0.3)
        return self._parse_json(raw, "resume", user_profile)

    # ── Cover letter (structured JSON) ──

    def _generate_cover_letter_json(self, job, user_profile) -> dict:
        prompt = f"""You are a professional cover letter writer.

CANDIDATE PROFILE:
{user_profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Output ONLY a valid JSON object (no markdown fences, no commentary):
{{
  "greeting": "Dear Hiring Manager,",
  "body": [
    "First paragraph — express interest in the role and company.",
    "Second paragraph — highlight relevant experience and skills.",
    "Third paragraph — closing statement and call to action."
  ],
  "closing": "Sincerely,"
}}

RULES:
- Reference the candidate's real skills and experience
- Keep it to 3-4 paragraphs
- Output valid JSON only"""

        raw = self.ollama.generate(prompt, max_tokens=1200, temperature=0.4)
        return self._parse_json(raw, "cover_letter", user_profile)

    # ── JSON parsing with fallback ──

    def _parse_json(self, text: str, doc_type: str, user_profile=None) -> dict:
        import json, re

        self.logger.debug(f"Raw LLM {doc_type} output ({len(text)} chars): {text[:300]}")

        # 1) Direct parse
        try:
            parsed = json.loads(text)
            self.logger.info(f"Parsed {doc_type} JSON directly (keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'not-dict'})")
            return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        # 2) Extract from markdown code fence
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(1))
                self.logger.info(f"Parsed {doc_type} JSON from code fence")
                return parsed
            except (json.JSONDecodeError, TypeError):
                pass

        # 3) Extract first { … } block
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                self.logger.info(f"Parsed {doc_type} JSON from brace extraction")
                return parsed
            except (json.JSONDecodeError, TypeError):
                pass

        self.logger.warning(f"Could not parse LLM {doc_type} output as JSON — using fallback. Raw: {text[:500]}")
        if doc_type == "resume":
            return self._fallback_resume(user_profile)
        return self._fallback_cover()

    def _fallback_resume(self, profile) -> dict:
        if profile is None:
            return {"summary": "", "experience": [], "education": [], "skills": [], "projects": [], "certifications": []}
        return {
            "summary": "",
            "experience": [str(e) for e in (profile.experience or [])],
            "education": [str(e) for e in (profile.education or [])],
            "skills": list(profile.skills or []),
            "projects": [str(p) for p in (profile.projects or [])],
            "certifications": list(profile.certifications or []),
        }

    def _fallback_cover(self) -> dict:
        return {"greeting": "Dear Hiring Manager,", "body": [], "closing": "Sincerely,"}

    # ── Legacy text helpers (kept for CLI agent) ──

    def _generate_resume_text(self, job, user_profile) -> str:
        prompt = f"""You are a professional resume writer. Create a tailored resume.

CANDIDATE PROFILE:
{user_profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Create a professional resume in Markdown format. Keep it concise (1 page) and focus on relevant qualifications."""

        return self.ollama.generate(prompt, max_tokens=1500, temperature=0.3)

    def _generate_cover_letter_text(self, job, user_profile) -> str:
        prompt = f"""You are a professional cover letter writer.

CANDIDATE PROFILE:
{user_profile.to_markdown()}

JOB DETAILS:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

Write a professional cover letter (3-4 paragraphs) in Markdown format."""

        return self.ollama.generate(prompt, max_tokens=1000, temperature=0.4)
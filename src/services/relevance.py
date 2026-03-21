"""LLM-based relevance scoring — compares a JD against a user profile."""

import logging
import re

from src.config.settings import config
from src.services.ollama import OllamaClient
from src.models.job import Job, UserProfile

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = int(config.app.relevance_threshold)


class RelevanceScorer:
    """Score how well a job description matches a user's profile using Ollama."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def score(self, job: Job, profile: UserProfile) -> int:
        """Return 0-100 relevance score. Higher = better match."""
        prompt = f"""You are a job-matching expert. Compare the JOB DESCRIPTION to the CANDIDATE PROFILE and return a single integer score from 0 to 100 representing how relevant this job is for this candidate.

Scoring guidance:
- 90-100: Almost perfect match — role, skills, and experience level align closely
- 70-89: Strong match — most key skills overlap, role type is compatible
- 50-69: Partial match — some skills overlap but role focus or seniority differs
- 30-49: Weak match — different specialisation despite similar field
- 0-29: Poor match — unrelated field or completely wrong seniority

Consider:
1. Do the REQUIRED SKILLS in the JD match the candidate's actual skills?
2. Is the ROLE TYPE (e.g. backend, frontend, DevOps, GRC, SOC) aligned with the candidate's experience?
3. Is the SENIORITY LEVEL appropriate for the candidate?
4. Would this job be a reasonable application for this candidate?

JOB DESCRIPTION:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{(job.description or "")[:2000]}

CANDIDATE PROFILE:
{profile.to_markdown()}

Respond with ONLY a single integer between 0 and 100. No other text."""

        try:
            raw = self.ollama.generate(prompt, max_tokens=20, temperature=0.1)
            return self._parse_score(raw)
        except Exception as e:
            logger.warning(f"Relevance scoring failed for {job.title}: {e}")
            return 0

    @staticmethod
    def _parse_score(text: str) -> int:
        nums = re.findall(r"\d+", text.strip())
        if nums:
            score = int(nums[0])
            return max(0, min(100, score))
        return 0

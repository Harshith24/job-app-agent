"""Domain models: Job, UserProfile, JobSearchCriteria, JobApplication."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Job:
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_date: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    source: Optional[str] = None

    @property
    def unique_key(self) -> str:
        return f"{self.title}|{self.company}|{self.url}"


@dataclass
class JobApplication:
    job: Job
    resume_text: str = ""
    cover_letter_text: str = ""
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class JobSearchCriteria:
    keywords: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    experience_levels: list[str] = field(default_factory=list)
    job_types: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, content: str) -> "JobSearchCriteria":
        """Parse a simple markdown-style criteria file."""
        sections = {
            "keywords": [],
            "locations": [],
            "experience_levels": [],
            "job_types": [],
            "exclude_terms": [],
        }
        header_to_section = {
            "role": "keywords", "keyword": "keywords",
            "location": "locations",
            "experience": "experience_levels", "level": "experience_levels",
            "employment": "job_types", "type": "job_types",
            "exclude": "exclude_terms",
        }

        current = None
        for line in content.lower().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            matched = next(
                (sec for keyword, sec in header_to_section.items() if keyword in line and ":" not in line),
                None,
            )
            if matched:
                current = matched
                continue

            if current and ":" in line:
                _, values = line.split(":", 1)
                sections[current].extend(v.strip() for v in values.split(",") if v.strip())

        return cls(
            keywords=sections["keywords"] or ["software engineer"],
            locations=sections["locations"] or ["remote"],
            experience_levels=sections["experience_levels"] or ["entry", "junior"],
            job_types=sections["job_types"] or ["full-time"],
            exclude_terms=sections["exclude_terms"],
        )


@dataclass
class UserProfile:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    experience: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, content: str) -> "UserProfile":
        profile = cls()
        current = None

        for raw in content.split("\n"):
            line = raw.strip()
            if not line:
                continue

            lower = line.lower()
            if lower.startswith("## "):
                key = lower[3:].strip()
                current = key if key in {"contact", "experience", "projects", "certifications", "education", "skills"} else None
                continue

            if current == "contact" and ":" in line:
                key, value = (p.strip() for p in line.split(":", 1))
                key = key.lstrip("-").strip().lower()
                if hasattr(profile, key):
                    setattr(profile, key, value)
            elif current and line.startswith("- "):
                getattr(profile, current).append(line[2:].strip())

        return profile

    def to_markdown(self) -> str:
        sections = []

        contact = [f"- {label}: {val}" for label, val in [
            ("Name", self.name), ("Email", self.email),
            ("Phone", self.phone), ("LinkedIn", self.linkedin),
            ("Location", self.location),
        ] if val]
        if contact:
            sections.append("## Contact\n" + "\n".join(contact))

        for title, items in [
            ("Experience", self.experience),
            ("Projects", self.projects),
            ("Certifications", self.certifications),
            ("Education", self.education),
            ("Skills", self.skills),
        ]:
            if items:
                sections.append(f"## {title}\n" + "\n".join(f"- {i}" for i in items))

        return "\n\n".join(sections)

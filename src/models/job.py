"""Job data models"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class Job:
    """Job posting data structure"""
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
        """Generate a unique key for deduplication"""
        return f"{self.title}|{self.company}|{self.url}"

@dataclass
class JobApplication:
    """Complete job application package"""
    job: Job
    resume_text: str = ""
    cover_letter_text: str = ""
    generated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()

@dataclass
class JobSearchCriteria:
    """Job search criteria"""
    keywords: list[str]
    locations: list[str]
    experience_levels: list[str]
    job_types: list[str]
    exclude_terms: list[str]

    @classmethod
    def from_markdown(cls, content: str) -> 'JobSearchCriteria':
        """Parse criteria from markdown content"""
        keywords = []
        locations = []
        experience_levels = []
        job_types = []
        exclude_terms = []

        lines = content.lower().split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Section headers
            if 'role' in line or 'keyword' in line:
                current_section = 'keywords'
                continue
            elif 'location' in line:
                current_section = 'locations'
                continue
            elif 'experience' in line or 'level' in line:
                current_section = 'experience'
                continue
            elif 'employment' in line or 'type' in line:
                current_section = 'job_types'
                continue
            elif 'exclude' in line:
                current_section = 'exclude'
                continue

            # Parse content
            if current_section and ':' in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    values = [v.strip() for v in parts[1].split(',') if v.strip()]
                    if current_section == 'keywords':
                        keywords.extend(values)
                    elif current_section == 'locations':
                        locations.extend(values)
                    elif current_section == 'experience':
                        experience_levels.extend(values)
                    elif current_section == 'job_types':
                        job_types.extend(values)
                    elif current_section == 'exclude':
                        exclude_terms.extend(values)

        return cls(
            keywords=keywords or ['software engineer'],
            locations=locations or ['remote'],
            experience_levels=experience_levels or ['entry', 'junior'],
            job_types=job_types or ['full-time'],
            exclude_terms=exclude_terms
        )

@dataclass
class UserProfile:
    """User professional profile"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None

    experience: list[str] = None
    projects: list[str] = None
    certifications: list[str] = None
    education: list[str] = None
    skills: list[str] = None

    def __post_init__(self):
        if self.experience is None:
            self.experience = []
        if self.projects is None:
            self.projects = []
        if self.certifications is None:
            self.certifications = []
        if self.education is None:
            self.education = []
        if self.skills is None:
            self.skills = []

    @classmethod
    def from_markdown(cls, content: str) -> 'UserProfile':
        """Parse profile from markdown content"""
        profile = cls()
        lines = content.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Section headers
            if '## contact' in line.lower():
                current_section = 'contact'
                continue
            elif '## experience' in line.lower():
                current_section = 'experience'
                continue
            elif '## projects' in line.lower():
                current_section = 'projects'
                continue
            elif '## certifications' in line.lower():
                current_section = 'certifications'
                continue
            elif '## education' in line.lower():
                current_section = 'education'
                continue
            elif '## skills' in line.lower():
                current_section = 'skills'
                continue

            # Parse content
            if current_section == 'contact' and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key == 'name':
                    profile.name = value
                elif key == 'email':
                    profile.email = value
                elif key == 'phone':
                    profile.phone = value
                elif key == 'linkedin':
                    profile.linkedin = value
                elif key == 'location':
                    profile.location = value
            elif current_section and line.startswith('- '):
                content = line[2:].strip()
                if current_section == 'experience':
                    profile.experience.append(content)
                elif current_section == 'projects':
                    profile.projects.append(content)
                elif current_section == 'certifications':
                    profile.certifications.append(content)
                elif current_section == 'education':
                    profile.education.append(content)
                elif current_section == 'skills':
                    profile.skills.append(content)

        return profile

    def to_markdown(self) -> str:
        """Convert profile to formatted markdown"""
        sections = []

        if any([self.name, self.email, self.phone, self.linkedin, self.location]):
            contact = ["## Contact"]
            if self.name:
                contact.append(f"- Name: {self.name}")
            if self.email:
                contact.append(f"- Email: {self.email}")
            if self.phone:
                contact.append(f"- Phone: {self.phone}")
            if self.linkedin:
                contact.append(f"- LinkedIn: {self.linkedin}")
            if self.location:
                contact.append(f"- Location: {self.location}")
            sections.append('\n'.join(contact))

        for section_name, items in [
            ("Experience", self.experience),
            ("Projects", self.projects),
            ("Certifications", self.certifications),
            ("Education", self.education),
            ("Skills", self.skills)
        ]:
            if items:
                section = [f"## {section_name}"]
                section.extend(f"- {item}" for item in items)
                sections.append('\n'.join(section))

        return '\n\n'.join(sections)
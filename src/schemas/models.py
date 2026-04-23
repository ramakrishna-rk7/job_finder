"""Pydantic schemas for Job Finder."""

from typing import List, Optional
from pydantic import BaseModel, Field


class StructuredQuery(BaseModel):
    """Output from Query Parser Agent."""
    keywords: List[str] = Field(description="Job search keywords")
    location: Optional[str] = Field(default=None, description="Location preference")
    remote: Optional[bool] = Field(default=None, description="Remote work preference")
    experience: Optional[str] = Field(default=None, description="Experience level (fresher/mid/senior)")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary in LPA")
    role: Optional[str] = Field(default=None, description="Primary job role")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    freshness: Optional[int] = Field(default=24, description="Max freshness hours (default 24hrs)")


class JobListing(BaseModel):
    """Individual job listing."""
    title: str = Field(description="Job title")
    company: str = Field(description="Company name")
    location: str = Field(description="Job location")
    url: str = Field(description="Job application URL")
    description: Optional[str] = Field(default=None, description="Job description snippet")
    salary: Optional[str] = Field(default=None, description="Salary range")
    posted_date: Optional[str] = Field(default=None, description="Posted date (raw text)")
    posted_time: Optional[str] = Field(default=None, description="Posted time (e.g., '2 hours ago', '1 day ago')")
    source: str = Field(default="google", description="Source platform")

    def is_recent(self, max_hours: int = 24) -> bool:
        """Check if job was posted recently (within max_hours)."""
        if not self.posted_time:
            return True

        text = self.posted_time.lower()

        if "just" in text or "now" in text or "hour" in text:
            hours_match = text.split()
            for i, w in enumerate(hours_match):
                if w.isdigit() and "hour" in hours_match[max(0, i-1):i+2]:
                    return int(w) <= max_hours
            return True

        if "day" in text:
            import re
            match = re.search(r'(\d+)\s*day', text)
            if match:
                days = int(match.group(1))
                return days <= 1

        if "week" in text:
            return False

        return True

    def get_experience_level(self) -> Optional[str]:
        """Infer experience level from title/description."""
        text = f"{self.title} {self.description or ''}".lower()

        fresher_keywords = ["intern", "fresher", "graduate", "trainee", "entry", "junior", "jr"]
        senior_keywords = ["senior", "lead", "principal", "sr", "manager"]

        for kw in fresher_keywords:
            if kw in text:
                return "fresher"
        for kw in senior_keywords:
            if kw in text:
                return "senior"

        return None


class JobFilterCriteria(BaseModel):
    """Criteria for Job Filter Agent."""
    required_skills: Optional[List[str]] = Field(default=None, description="Must-have skills")
    location_match: Optional[bool] = Field(default=True, description="Location must match")
    experience_level: Optional[str] = Field(default=None, description="Experience level filter")
    max_posted_hours: int = Field(default=24, description="Max hours since posted")


class MatchResult(BaseModel):
    """Output from Resume Matcher Agent."""
    job: JobListing
    match_score: int = Field(description="Match score 0-100", ge=0, le=100)
    matched_skills: List[str] = Field(description="Skills found in both resume and job")
    missing_skills: List[str] = Field(description="Skills required by job but not in resume")
    reasoning: str = Field(description="Explanation of match score")


class RankedJob(BaseModel):
    """Job with multi-factor ranking."""
    job: JobListing
    skill_score: int = Field(default=0, description="Skill match score 0-100")
    freshness_score: int = Field(default=0, description="Freshness score 0-100")
    title_match_score: int = Field(default=0, description="Title match score 0-100")
    location_score: int = Field(default=0, description="Location match score 0-100")
    final_score: int = Field(description="Final weighted score 0-100", ge=0, le=100)
    reason: str = Field(description="Explanation of scoring")


class SearchResult(BaseModel):
    """Complete search result."""
    query: StructuredQuery
    jobs: List[JobListing]
    filtered_count: int = Field(description="Number of jobs after filtering")
    recent_count: int = Field(description="Number of recent jobs")
    matched_jobs: Optional[List[MatchResult]] = Field(default=None, description="Jobs matched with resume")
    ranked_jobs: Optional[List[RankedJob]] = Field(default=None, description="Jobs ranked by AI")
    telegram_sent: bool = Field(default=False, description="Whether notification was sent")


class UserPreferences(BaseModel):
    """User saved preferences."""
    user_id: str = Field(description="Telegram chat ID or user identifier")
    resume_text: Optional[str] = Field(default=None, description="User resume as text")
    default_keywords: List[str] = Field(default_factory=list, description="Default search keywords")
    default_location: Optional[str] = Field(default=None, description="Default location")
    notify_telegram: bool = Field(default=True, description="Send Telegram notifications")
    notify_daily: bool = Field(default=False, description="Enable daily alerts")
    daily_time: Optional[str] = Field(default="09:00", description="Daily alert time (HH:MM)")
    experience_filter: str = Field(default="fresher", description="Preferred experience level")


def filter_recent_jobs(jobs: List[JobListing], max_hours: int = 24) -> List[JobListing]:
    """Filter jobs posted within max_hours."""
    return [job for job in jobs if job.is_recent(max_hours)]


def filter_by_experience(jobs: List[JobListing], level: str = "fresher") -> List[JobListing]:
    """Filter jobs by experience level."""
    if not level:
        return jobs
    return [job for job in jobs if job.get_experience_level() == level]


def sort_by_recent(jobs: List[JobListing]) -> List[JobListing]:
    """Sort jobs by recency."""
    priority_order = {"just": 0, "now": 0, "hour": 1, "day": 2, "week": 3, "month": 4}

    def get_priority(job: JobListing) -> int:
        text = (job.posted_time or "").lower()
        for key, prio in priority_order.items():
            if key in text:
                return prio
        return 5

    return sorted(jobs, key=get_priority)
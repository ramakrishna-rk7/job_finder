"""Ranker Agent - Multi-factor job ranking with HuggingFace."""

import os
import json
from typing import List, Optional
import httpx

from ..schemas.models import JobListing, RankedJob, StructuredQuery
from ..utils.time_utils import extract_hours, format_freshness
from ..config.settings import HF_TOKEN, HF_MODEL


SKILL_WEIGHT = 0.4
FRESHNESS_WEIGHT = 0.3
TITLE_WEIGHT = 0.2
LOCATION_WEIGHT = 0.1


def calculate_skill_score(job: JobListing, resume_skills: List[str]) -> int:
    """Calculate skill match score."""
    if not resume_skills:
        return 50
    
    job_text = f"{job.title} {job.description or ''}".lower()
    resume_lower = [s.lower() for s in resume_skills]
    
    matches = sum(1 for skill in resume_lower if skill in job_text)
    
    if not matches:
        return 20
    
    return min(100, 50 + matches * 15)


def calculate_freshness_score(job: JobListing, max_hours: int = 24) -> int:
    """Calculate freshness score."""
    if not job.posted_time:
        return 30
    
    hours = extract_hours(job.posted_time)
    
    if hours <= 1:
        return 100
    elif hours <= 6:
        return 90
    elif hours <= 12:
        return 80
    elif hours <= 24:
        return 70
    elif hours <= 48:
        return 50
    elif hours <= 72:
        return 30
    else:
        return 10


def calculate_title_match(job: JobListing, keywords: List[str]) -> int:
    """Calculate title match score."""
    if not keywords:
        return 50
    
    title_lower = job.title.lower()
    
    matches = sum(1 for kw in keywords if kw.lower() in title_lower)
    
    if not matches:
        return 25
    
    return min(100, matches * 35)


def calculate_location_score(job: JobListing, preferred_location: Optional[str]) -> int:
    """Calculate location match score."""
    if not preferred_location:
        return 50
    
    job_location = job.location.lower()
    preferred = preferred_location.lower()
    
    if preferred == "remote" or "remote" in job_location:
        return 100
    
    if preferred in job_location:
        return 90
    
    common_cities = ["bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "pune", "chennai"]
    for city in common_cities:
        if city in job_location and city in preferred:
            return 70
    
    return 40


def rank_jobs(
    jobs: List[JobListing],
    query: StructuredQuery,
    resume_skills: Optional[List[str]] = None
) -> List[RankedJob]:
    """Rank jobs using multi-factor scoring."""
    if not jobs:
        return []
    
    resume_skills = resume_skills or []
    location = query.location
    
    ranked = []
    
    for job in jobs:
        skill_score = calculate_skill_score(job, resume_skills)
        freshness_score = calculate_freshness_score(job, query.freshness or 24)
        title_score = calculate_title_match(job, query.keywords)
        location_score = calculate_location_score(job, location)
        
        final_score = int(
            skill_score * SKILL_WEIGHT +
            freshness_score * FRESHNESS_WEIGHT +
            title_score * TITLE_WEIGHT +
            location_score * LOCATION_WEIGHT
        )
        
        reason = _generate_reason(
            skill_score,
            freshness_score,
            title_score,
            location_score,
            job
        )
        
        ranked.append(RankedJob(
            job=job,
            skill_score=skill_score,
            freshness_score=freshness_score,
            title_match_score=title_score,
            location_score=location_score,
            final_score=final_score,
            reason=reason
        ))
    
    ranked.sort(key=lambda x: x.final_score, reverse=True)
    return ranked


def _generate_reason(skill: int, freshness: int, title: int, location: int, job: JobListing) -> str:
    """Generate scoring explanation."""
    parts = []
    
    if freshness >= 80:
        parts.append("recent")
    elif freshness >= 50:
        parts.append("somewhat recent")
    
    if skill >= 70:
        parts.append("good skills")
    elif skill >= 40:
        parts.append("partial match")
    
    if title >= 70:
        parts.append("title matches")
    
    if location >= 70:
        parts.append("good location")
    
    if not parts:
        return "Standard match"
    
    return ", ".join(parts)


async def rank_jobs_with_huggingface(
    jobs: List[JobListing],
    query: StructuredQuery,
    resume_skills: Optional[List[str]] = None
) -> List[RankedJob]:
    """Rank jobs using HuggingFace DeepSeek-R1 for enhanced scoring."""
    # Skip HF ranking - just use basic ranking
    return rank_jobs(jobs, query, resume_skills)


def format_ranked_jobs(
    ranked: List[RankedJob],
    max_jobs: int = 5
) -> str:
    """Format ranked jobs for display."""
    if not ranked:
        return "No matching jobs found."
    
    message = "🔥 *Latest Jobs*\n\n"
    
    for i, ranked_job in enumerate(ranked[:max_jobs], 1):
        job = ranked_job.job
        message += f"*{i}. {job.title}* @{job.company}\n"
        message += f"   🕐 {job.posted_time or 'Unknown time'}\n"
        message += f"   📍 {job.location}\n"
        message += f"   📊 Score: {ranked_job.final_score}%\n"
        if job.url:
            message += f"   🔗 [Apply]({job.url})\n"
        message += "\n"
    
    message += f"_Showing {min(max_jobs, len(ranked))} of {len(ranked)} jobs_"
    return message


if __name__ == "__main__":
    from src.schemas.models import StructuredQuery
    
    query = StructuredQuery(
        keywords=["Python", "Developer"],
        location="India",
        freshness=24
    )
    
    jobs = [
        JobListing(
            title="Python Developer",
            company="Infosys",
            location="Bangalore",
            url="https://example.com",
            posted_time="2 hours ago",
            source="indeed"
        ),
        JobListing(
            title="ML Engineer",
            company="Startup",
            location="Remote",
            url="https://example2.com",
            posted_time="5 hours ago",
            source="indeed"
        ),
    ]
    
    ranked = rank_jobs(jobs, query)
    for r in ranked:
        print(f"{r.job.title}: {r.final_score}% - {r.reason}")
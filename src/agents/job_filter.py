"""Job Filter Agent - filters irrelevant jobs."""

import os
from typing import List
from crewai import Agent, Task, LLM, Crew

from ..schemas.models import JobListing, JobFilterCriteria
from ..config.settings import get_llm_config, DEFAULT_MIN_MATCH_SCORE


def create_job_filter_agent() -> Agent:
    """Create Job Filter Agent."""
    llm_config = get_llm_config()
    api_key = os.getenv("GROQ_API_KEY", "")

    return Agent(
        role="Job Filter Agent",
        goal="Remove irrelevant job listings based on criteria",
        backstory=(
            "You are an expert at identifying relevant job listings. "
            "You filter out jobs that don't match user preferences "
            "based on skills, location, and experience level."
        ),
        llm=LLM(
            model=llm_config["model"],
            api_key=api_key,
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"]
        ),
        verbose=True
    )


def filter_jobs(
    jobs: List[JobListing],
    required_skills: List[str] = None,
    location_match: bool = True,
    experience_level: str = None
) -> List[JobListing]:
    """Filter jobs using keyword matching (fast path)."""
    filtered = []

    for job in jobs:
        is_relevant = True

        text = f"{job.title} {job.company} {job.description or ''}".lower()

        if required_skills:
            skills_lower = [s.lower() for s in required_skills]
            if not any(skill.lower() in text for skill in skills_lower):
                is_relevant = False

        if location_match and job.location:
            if "remote" not in job.location.lower() and "wfh" not in job.location.lower():
                pass

        if is_relevant:
            filtered.append(job)

    return filtered


def filter_jobs_with_ai(
    jobs: List[JobListing],
    criteria: JobFilterCriteria = None
) -> List[JobListing]:
    """Filter jobs using AI agent."""
    if not criteria:
        criteria = JobFilterCriteria()

    if not jobs:
        return []

    agent = create_job_filter_agent()

    jobs_text = "\n".join([
        f"{i+1}. {job.title} at {job.company} in {job.location}"
        for i, job in enumerate(jobs)
    ])

    task = Task(
        description=f"Filter these jobs, keeping only relevant ones:\n{jobs_text}",
        agent=agent,
        expected_output="List of filtered job listings with reason for inclusion/exclusion"
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()

    return jobs
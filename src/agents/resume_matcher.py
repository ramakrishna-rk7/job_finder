"""Resume Matcher Agent - matches jobs with resume."""

import os
from typing import List
from crewai import Agent, Task, LLM, Crew

from ..schemas.models import JobListing, MatchResult
from ..config.settings import get_llm_config


def create_resume_matcher_agent() -> Agent:
    """Create Resume Matcher Agent."""
    llm_config = get_llm_config()
    api_key = os.getenv("GROQ_API_KEY", "")

    return Agent(
        role="Resume Matcher Agent",
        goal="Match jobs with user resume and calculate match scores",
        backstory=(
            "You are an expert at resume-job matching. You analyze job requirements "
            "and compare them with candidate skills to calculate match scores "
            "and identify skill gaps."
        ),
        llm=LLM(
            model=llm_config["model"],
            api_key=api_key,
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"]
        ),
        verbose=True
    )


def extract_skills_from_resume(resume_text: str) -> List[str]:
    """Extract skills from resume text using keyword matching."""
    common_skills = [
        "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
        "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
        "sql", "mysql", "postgresql", "mongodb", "redis",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "git", "jenkins", "ci/cd", "agile", "scrum",
        "machine learning", "deep learning", "tensorflow", "pytorch", "nlp",
        "html", "css", "rest api", "graphql",
        "linux", "bash", "shell scripting",
        "data analysis", "data science", "pandas", "numpy", "excel",
        "communication", "leadership", "problem solving", "teamwork"
    ]

    resume_lower = resume_text.lower()
    found_skills = [skill for skill in common_skills if skill in resume_lower]
    return found_skills


def calculate_match_score(resume_skills: List[str], job: JobListing) -> tuple[int, list[str], list[str]]:
    """Calculate match score between resume and job."""
    job_text = f"{job.title} {job.company} {job.description or ''}".lower()

    required_python = "python" in job_text
    required_javascript = "javascript" in job_text or "js" in job_text
    required_react = "react" in job_text
    required_ml = "machine learning" in job_text or "ml" in job_text
    required_sql = "sql" in job_text

    job_required_skills = []
    if required_python:
        job_required_skills.append("python")
    if required_javascript:
        job_required_skills.append("javascript")
    if required_react:
        job_required_skills.append("react")
    if required_ml:
        job_required_skills.append("machine learning")
    if required_sql:
        job_required_skills.append("sql")

    resume_skills_lower = [s.lower() for s in resume_skills]

    matched = [s for s in job_required_skills if s in resume_skills_lower]
    missing = [s for s in job_required_skills if s not in resume_skills_lower]

    if not job_required_skills:
        base_score = 50
    else:
        base_score = int(100 * len(matched) / len(job_required_skills))

    bonus = 10 if matched else 0
    score = min(100, base_score + bonus)

    return score, matched, missing


def match_jobs_with_resume(
    jobs: List[JobListing],
    resume_text: str
) -> List[MatchResult]:
    """Match jobs with resume using fast keyword matching."""
    if not resume_text or not jobs:
        return []

    resume_skills = extract_skills_from_resume(resume_text)
    results = []

    for job in jobs:
        score, matched, missing = calculate_match_score(resume_skills, job)
        reason = 'Matched: ' + (', '.join(matched) if matched else 'None') + '. '
        reason += 'Missing: ' + (', '.join(missing) if missing else 'None')

        results.append(MatchResult(
            job=job,
            match_score=score,
            matched_skills=matched,
            missing_skills=missing,
            reason=reason
        ))

    results.sort(key=lambda x: x.match_score, reverse=True)
    return results


def match_jobs_with_ai(
    jobs: List[JobListing],
    resume_text: str
) -> List[MatchResult]:
    """Match jobs with resume using AI agent."""
    if not resume_text or not jobs:
        return []

    agent = create_resume_matcher_agent()

    jobs_list = []
    for i, job in enumerate(jobs[:5]):
        jobs_list.append(f"{i+1}. {job.title} at {job.company}")
    jobs_text = "\n".join(jobs_list)

    task = Task(
        description=f"Match jobs:\n{resume_text[:500]}\n\nJobs:\n{jobs_text}",
        agent=agent,
        expected_output="Match scores and skill gaps"
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()

    return match_jobs_with_resume(jobs, resume_text)
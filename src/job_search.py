"""Job Search pipeline module."""

import asyncio
import os
from typing import List, Optional
from crewai import Task, Crew

from .schemas.models import (
    StructuredQuery,
    JobListing,
    MatchResult,
    SearchResult,
    RankedJob
)
from .config.settings import DEFAULT_MAX_JOBS, DEFAULT_MIN_MATCH_SCORE, HF_TOKEN
from .tools.scrapers import MultiSourceDispatcher
from .agents.query_parser import parse
from .agents.job_filter import filter_jobs
from .agents.resume_matcher import match_jobs_with_resume
from .agents.ranker import rank_jobs, rank_jobs_with_huggingface, format_ranked_jobs
from .services.storage import add_jobs
from .utils.time_utils import is_recent_job


__all__ = [
    "search",
    "search_simple",
    "run_search",
    "run_prompt_search"
]


async def run_prompt_search(
    prompt: str,
    resume_text: Optional[str] = None,
    max_results: int = DEFAULT_MAX_JOBS,
    send_notification: bool = False,
    use_ai_parsing: bool = True
) -> SearchResult:
    """User Prompt-Based Job Search Pipeline."""
    print(f"\n=== Input: {prompt} ===")

    query = parse(prompt, use_ai=use_ai_parsing)
    print(f"Parsed Query:")
    print(f"   Keywords: {query.keywords}")
    print(f"   Role: {query.role}")
    print(f"   Location: {query.location}")
    print(f"   Remote: {query.remote}")
    print(f"   Experience: {query.experience}")
    print(f"   Freshness: <={query.freshness}hrs")

    print(f"\n Scraping from multiple sources...")
    
    dispatcher = MultiSourceDispatcher(
        enable_indeed=True,
        enable_naukri=True,
        enable_linkedin=True,
        enable_google=True,
        headless=True,
        max_freshness_hours=query.freshness or 24,
        delay_between_sources=0.5
    )
    
    scrape_result = await dispatcher.scrape_all(query, max_results)
    
    jobs = scrape_result.jobs
    print(f"Found {len(jobs)} jobs from {scrape_result.source_counts}")

    filtered = filter_jobs(jobs)
    print(f"Filtered: {len(filtered)} jobs")

    resume_skills = None
    if resume_text:
        from .agents.resume_matcher import extract_skills_from_resume
        resume_skills = extract_skills_from_resume(resume_text)
        print(f"Resume skills: {resume_skills}")

    ranked_jobs = None
    if HF_TOKEN:
        ranked_jobs = await rank_jobs_with_huggingface(filtered, query, resume_skills)
    else:
        ranked_jobs = rank_jobs(filtered, query, resume_skills)
    
    if ranked_jobs:
        matched_skills = [r for r in ranked_jobs if r.final_score >= DEFAULT_MIN_MATCH_SCORE]
        matched_jobs = [
            MatchResult(
                job=r.job,
                match_score=r.final_score,
                matched_skills=[],
                missing_skills=[],
                reasoning=r.reason
            )
            for r in matched_skills[:5]
        ]
        print(f"Ranked: {len(ranked_jobs)} jobs")

    if filtered:
        add_jobs(filtered)

    result = SearchResult(
        query=query,
        jobs=filtered,
        filtered_count=len(filtered),
        recent_count=len(filtered),
        matched_jobs=matched_jobs,
        ranked_jobs=ranked_jobs[:5] if ranked_jobs else None,
        telegram_sent=send_notification and bool(ranked_jobs)
    )

    print(f"\n=== Complete! {len(filtered)} jobs found ===\n")

    return result


async def search(
    prompt: str,
    resume_text: Optional[str] = None,
    max_results: int = DEFAULT_MAX_JOBS,
    send_notification: bool = False
) -> SearchResult:
    """Main search function (alias for run_prompt_search)."""
    return await run_prompt_search(prompt, resume_text, max_results, send_notification)


async def search_simple(
    keywords: List[str],
    location: str = None,
    remote: bool = False,
    max_results: int = DEFAULT_MAX_JOBS
) -> List[JobListing]:
    """Simple search with raw keywords."""
    from .tools.scrapers import MultiSourceDispatcher
    
    query = StructuredQuery(
        keywords=keywords,
        location=location,
        remote=remote,
        freshness=24
    )

    async with MultiSourceDispatcher() as dispatcher:
        result = await dispatcher.scrape_all(query, max_results)
        jobs = result.jobs

    if jobs:
        add_jobs(jobs)

    return jobs


async def run_quick_search(
    keywords: List[str],
    location: str = None,
    max_results: int = DEFAULT_MAX_JOBS
) -> SearchResult:
    """Quick search - simpler interface."""
    return await search_simple(keywords, location, max_results=max_results)


def run_search(
    prompt: str,
    resume_path: str = None,
    max_results: int = DEFAULT_MAX_JOBS,
    send_notification: bool = False
) -> SearchResult:
    """Synchronous search wrapper."""
    resume_text = None
    if resume_path and os.path.exists(resume_path):
        from .tools.file_tools import read_resume
        resume_text = read_resume(resume_path)

    return asyncio.run(run_prompt_search(
        prompt,
        resume_text,
        max_results,
        send_notification
    ))


if __name__ == "__main__":
    test_prompts = [
        "Remote AI jobs for freshers in India",
        "Python developer",
        "React fresher",
    ]

    for prompt in test_prompts:
        result = asyncio.run(run_prompt_search(prompt, max_results=5))
        print(f"Results: {len(result.jobs)} jobs")
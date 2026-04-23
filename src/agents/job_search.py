"""Job Search Agent - executes scraper and processes results."""

import asyncio
import os
from typing import List
from crewai import Agent, Task, LLM, Crew

from ..schemas.models import JobListing, StructuredQuery
from ..config.settings import get_llm_config
from ..tools.scraper import GoogleJobsScraper


def create_job_search_agent() -> Agent:
    """Create Job Search Agent."""
    llm_config = get_llm_config()
    api_key = os.getenv("GROQ_API_KEY", "")

    return Agent(
        role="Job Search Agent",
        goal="Find relevant job listings based on structured queries",
        backstory=(
            "You are an expert job searcher. You know how to find relevant "
            "job listings from various sources and extract key information "
            "like title, company, location, and URL."
        ),
        llm=LLM(
            model=llm_config["model"],
            api_key=api_key,
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"]
        ),
        verbose=True
    )


async def scrape_jobs_task(
    query: StructuredQuery,
    max_results: int = 20
) -> List[JobListing]:
    """Scrape jobs using Playwright."""
    async with GoogleJobsScraper(headless=True) as scraper:
        jobs = await scraper.scrape(query, max_results)
    return jobs


def create_job_search_with_crew(query: StructuredQuery, max_results: int = 20) -> List[JobListing]:
    """Create a CrewAI task for job search."""
    agent = create_job_search_agent()

    keywords = ", ".join(query.keywords)
    task = Task(
        description=f"Search for {keywords} jobs in {query.location or 'any location'}"
                   f"{' (remote only)' if query.remote else ''}",
        agent=agent,
        expected_output="List of job listings with title, company, location, and URL"
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    crew.kickoff()

    return asyncio.run(scrape_jobs_task(query, max_results))
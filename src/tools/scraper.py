"""Job scraper - Multi-source job scraping.

This module now re-exports from the new scrapers package.
For direct usage, import from src.tools.scrapers instead.
"""

from .scrapers import MultiSourceDispatcher
from .scrapers import IndeedScraper, NaukriScraper, LinkedInScraper, GoogleJobsScraper

__all__ = [
    "MultiSourceDispatcher",
    "IndeedScraper",
    "NaukriScraper",
    "LinkedInScraper",
    "GoogleJobsScraper",
]


class JobScraper:
    """Simple HTTP scraper (legacy - use MultiSourceDispatcher)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def scrape(self, query, max_results: int = 20):
        """Scrape jobs (legacy interface)."""
        from .scrapers.dispatcher import scrape_jobs
        result = await scrape_jobs(query, max_results)
        return result.jobs


async def scrape_jobs(keywords, location=None, remote=None, experience=None, max_results=20, source="all"):
    """Convenience function."""
    from ..schemas.models import StructuredQuery
    from .scrapers.dispatcher import scrape_jobs
    
    query = StructuredQuery(
        keywords=keywords,
        location=location,
        remote=remote,
        experience=experience,
        freshness=24
    )
    
    result = await scrape_jobs(query, max_results)
    return result.jobs


if __name__ == "__main__":
    import asyncio
    
    async def test():
        from src.schemas.models import StructuredQuery
        from src.tools.scrapers import MultiSourceDispatcher
        
        query = StructuredQuery(
            keywords=["python", "developer"],
            location="India",
            freshness=24
        )
        
        dispatcher = MultiSourceDispatcher()
        result = await dispatcher.scrape_all(query, max_results=10)
        
        print(f"Found {len(result.jobs)} jobs:")
        for job in result.jobs:
            print(f"- {job.title} @ {job.company}")
            print(f"  🕐 {job.posted_time} | {job.location}")
    
    asyncio.run(test())
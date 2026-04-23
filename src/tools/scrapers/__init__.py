"""Scrapers module - Multi-source job scraping.

Usage:
    from src.tools.scrapers import MultiSourceDispatcher
    from src.schemas.models import StructuredQuery
    
    query = StructuredQuery(keywords=["python", "developer"], location="India")
    dispatcher = MultiSourceDispatcher()
    result = await dispatcher.scrape_all(query, max_results=20)
"""

from .base import BaseScraper, ScrapedJob, DeduplicationEngine
from .indeed import IndeedScraper
from .naukri import NaukriScraper
from .linkedin import LinkedInScraper
from .google_jobs import GoogleJobsScraper
from .dispatcher import MultiSourceDispatcher, ScrapeResult

__all__ = [
    "BaseScraper",
    "ScrapedJob",
    "DeduplicationEngine",
    "IndeedScraper",
    "NaukriScraper",
    "LinkedInScraper",
    "GoogleJobsScraper",
    "MultiSourceDispatcher",
    "ScrapeResult",
]
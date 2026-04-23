"""Multi-source scraper dispatcher."""

import asyncio
from typing import List, Optional
from dataclasses import dataclass

from ...schemas.models import JobListing, StructuredQuery
from ...utils.time_utils import extract_hours, is_recent_job
from .indeed import IndeedScraper
from .naukri import NaukriScraper
from .linkedin import LinkedInScraper
from .google_jobs import GoogleJobsScraper
from .http_scraper import URLJobScraper


@dataclass
class ScrapeResult:
    """Result from multi-source scrape."""
    jobs: List[JobListing]
    source_counts: dict
    errors: List[str]


class MultiSourceDispatcher:
    """Run multiple scrapers and merge results."""
    
    def __init__(
        self,
        enable_indeed: bool = True,
        enable_naukri: bool = True,
        enable_linkedin: bool = True,
        enable_google: bool = True,
        headless: bool = True,
        max_freshness_hours: int = 24,
        delay_between_sources: float = 0.5
    ):
        self.enable_indeed = enable_indeed
        self.enable_naukri = enable_naukri
        self.enable_linkedin = enable_linkedin
        self.enable_google = enable_google
        self.headless = headless
        self.max_freshness_hours = max_freshness_hours
        self.delay_between_sources = delay_between_sources
    
    async def scrape_all(
        self,
        query: StructuredQuery,
        max_results: int = 20
    ) -> ScrapeResult:
        """Scrape from all enabled sources."""
        keywords = query.keywords
        location = query.location
        all_jobs = []
        source_counts = {}
        errors = []
        
        if not all_jobs:
            try:
                async with URLJobScraper() as scraper:
                    url_jobs = await scraper.scrape(keywords, location, max_results)
                    all_jobs.extend(url_jobs)
                    source_counts["url"] = len(url_jobs)
            except Exception as e:
                errors.append(f"URL: {str(e)}")
        
        if self.enable_indeed:
            try:
                scraper = IndeedScraper(headless=self.headless)
                await scraper.start()
                jobs = await scraper.scrape_jobs(keywords, location, max_results)
                await scraper.close()
                if jobs:
                    all_jobs.extend(jobs)
                    source_counts["indeed"] = len(jobs)
            except Exception as e:
                print(f"Indeed error: {e}")
                errors.append(f"indeed: {str(e)}")
        
        await asyncio.sleep(self.delay_between_sources)
        
        if self.enable_naukri:
            try:
                scraper = NaukriScraper(headless=self.headless)
                await scraper.start()
                jobs = await scraper.scrape_jobs(keywords, location, max_results)
                await scraper.close()
                if jobs:
                    all_jobs.extend(jobs)
                    source_counts["naukri"] = len(jobs)
            except Exception as e:
                print(f"Naukri error: {e}")
                errors.append(f"naukri: {str(e)}")
        
        await asyncio.sleep(self.delay_between_sources)
        
        if self.enable_linkedin:
            try:
                scraper = LinkedInScraper(headless=self.headless)
                await scraper.start()
                jobs = await scraper.scrape_jobs(keywords, location, max_results)
                await scraper.close()
                if jobs:
                    all_jobs.extend(jobs)
                    source_counts["linkedin"] = len(jobs)
            except Exception as e:
                print(f"LinkedIn error: {e}")
                errors.append(f"linkedin: {str(e)}")
        
        await asyncio.sleep(self.delay_between_sources)
        
        if self.enable_google:
            try:
                scraper = GoogleJobsScraper(headless=self.headless)
                await scraper.start()
                jobs = await scraper.scrape_jobs(keywords, location, max_results)
                await scraper.close()
                if jobs:
                    all_jobs.extend(jobs)
                    source_counts["google"] = len(jobs)
            except Exception as e:
                print(f"Google error: {e}")
                errors.append(f"google: {str(e)}")
        
        all_jobs = self._deduplicate(all_jobs)
        
        all_jobs.sort(key=lambda j: extract_hours(j.posted_time) if j.posted_time else 999)
        
        all_jobs = all_jobs[:max_results]
        
        return ScrapeResult(
            jobs=all_jobs,
            source_counts=source_counts,
            errors=errors
        )
    
    async def _scrape_indeed(
        self,
        keywords: List[str],
        location: Optional[str],
        max_results: int
    ) -> List[JobListing]:
        """Scrape Indeed."""
        try:
            scraper = IndeedScraper(headless=self.headless)
            await scraper.start()
            jobs = await scraper.scrape_jobs(keywords, location, max_results)
            await scraper.close()
            return jobs
        except Exception as e:
            print(f"Indeed error: {e}")
            return []
    
    async def _scrape_naukri(
        self,
        keywords: List[str],
        location: Optional[str],
        max_results: int
    ) -> List[JobListing]:
        """Scrape Naukri."""
        try:
            scraper = NaukriScraper(headless=self.headless)
            await scraper.start()
            jobs = await scraper.scrape_jobs(keywords, location, max_results)
            await scraper.close()
            return jobs
        except Exception as e:
            print(f"Naukri error: {e}")
            return []
    
    async def _scrape_linkedin(
        self,
        keywords: List[str],
        location: Optional[str],
        max_results: int
    ) -> List[JobListing]:
        """Scrape LinkedIn via Google."""
        try:
            scraper = LinkedInScraper(headless=self.headless)
            await scraper.start()
            jobs = await scraper.scrape_jobs(keywords, location, max_results)
            await scraper.close()
            return jobs
        except Exception as e:
            print(f"LinkedIn error: {e}")
            return []
    
    async def _scrape_google(
        self,
        keywords: List[str],
        location: Optional[str],
        max_results: int
    ) -> List[JobListing]:
        """Scrape Google Jobs."""
        try:
            scraper = GoogleJobsScraper(headless=self.headless)
            await scraper.start()
            jobs = await scraper.scrape_jobs(keywords, location, max_results)
            await scraper.close()
            return jobs
        except Exception as e:
            print(f"Google Jobs error: {e}")
            return []
    
    def _deduplicate(self, jobs: List[JobListing]) -> List[JobListing]:
        """Remove duplicate jobs."""
        seen_urls = set()
        seen_titles = set()
        unique = []
        
        for job in jobs:
            if job.url and job.url in seen_urls:
                continue
            
            title_key = job.title.lower().replace(" ", "")
            if title_key in seen_titles:
                continue
            
            if job.url:
                seen_urls.add(job.url)
            seen_titles.add(title_key)
            unique.append(job)
        
        return unique


async def scrape_jobs(
    query: StructuredQuery,
    max_results: int = 20,
    max_freshness_hours: int = 24
) -> ScrapeResult:
    """Convenience function."""
    dispatcher = MultiSourceDispatcher(max_freshness_hours=max_freshness_hours)
    return await dispatcher.scrape_all(query, max_results)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        from src.schemas.models import StructuredQuery
        
        query = StructuredQuery(
            keywords=["python", "developer"],
            location="India",
            remote=True
        )
        
        result = await scrape_jobs(query, max_results=10)
        
        print(f"\nFound {len(result.jobs)} jobs:")
        for job in result.jobs:
            print(f"- {job.title} @ {job.company}")
            print(f"  {job.posted_time} | {job.url}")
    
    asyncio.run(test())
"""Naukri scraper - India-focused job listings."""

import re
from typing import List, Optional

from .base import BaseScraper, ScrapedJob
from ...utils.time_utils import parse_naukri_time


class NaukriScraper(BaseScraper):
    """Naukri job scraper (India)."""
    
    BASE_URL = "https://www.naukri.com"
    SEARCH_URL = "https://www.naukri.com/jobs"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """Scrape jobs from Naukri."""
        query = "-".join(keywords)
        location = location or "India"
        
        url = (
            f"{self.SEARCH_URL}?"
            f"q={query}"
            f"&l={location}"
            f"&sort=date"
            f"&[Experience]=0-3"
        )
        
        jobs = []
        
        try:
            async with (await self.new_page()) as page:
                await page.goto(url, wait_until="domcontentloaded")
                await self._human_delay()
                await self._scroll_page(page, scrolls=3)
                
                html = await page.content()
                jobs = self._parse_jobs(html)
        except Exception as e:
            print(f"Naukri scrape error: {e}")
        
        return jobs[:max_results]
    
    def _parse_jobs(self, html: str) -> List[ScrapedJob]:
        """Parse Naukri job listings."""
        soup = self._parse_html(html)
        jobs = []
        
        job_cards = soup.select('div.jobTuple')
        if not job_cards:
            job_cards = soup.select('article.jobTuple')
        
        for card in job_cards:
            try:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)
            except Exception:
                continue
        
        return jobs
    
    def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse individual job card."""
        title_elem = (
            card.select_one('a.title') or
            card.select_one('span.title') or
            card.select_one('[class*="title"]')
        )
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        link_elem = card.select_one('a.title')
        
        url = ""
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
        
        company_elem = (
            card.select_one('a.company') or
            card.select_one('span.company') or
            card.select_one('[class*="companyInfo"]')
        )
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
        
        location_elem = (
            card.select_one('span.location') or
            card.select_one('li.location') or
            card.select_one('[class*="location"]')
        )
        location = location_elem.get_text(strip=True) if location_elem else "Unknown"
        
        time_elem = (
            card.select_one('span.posted') or
            card.select_one('[class*="posted"]') or
            card.select_one('span.fade-info')
        )
        posted_time = time_elem.get_text(strip=True) if time_elem else None
        
        salary_elem = (
            card.select_one('span.salary') or
            card.select_one('[class*="salary"]')
        )
        salary = salary_elem.get_text(strip=True) if salary_elem else None
        
        exp_elem = card.select_one('span.experience')
        experience = exp_elem.get_text(strip=True) if exp_elem else None
        
        return ScrapedJob(
            title=title,
            company=company,
            location=location,
            url=url,
            posted_time=posted_time,
            salary=salary,
            description=experience,
            source="naukri"
        )
    
    def get_source_name(self) -> str:
        return "naukri"


async def scrape_naukri_jobs(
    keywords: List[str],
    location: Optional[str] = None,
    max_results: int = 20
) -> List[ScrapedJob]:
    """Convenience function."""
    async with NaukriScraper(headless=True) as scraper:
        return await scraper.scrape(keywords, location, max_results)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        async with NaukriScraper(headless=False) as scraper:
            jobs = await scraper.scrape(["python", "developer"], "India", 5)
            for job in jobs:
                print(f"- {job.title} at {job.company}")
    
    asyncio.run(test())
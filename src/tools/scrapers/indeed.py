"""Indeed scraper - Primary source for job listings."""

import re
from typing import List, Optional

from .base import BaseScraper, ScrapedJob
from ...utils.time_utils import parse_indeed_time


class IndeedScraper(BaseScraper):
    """Indeed job scraper."""
    
    BASE_URL = "https://www.indeed.com"
    SEARCH_URL = "https://www.indeed.com/jobs"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """Scrape jobs from Indeed."""
        query = "+".join(keywords)
        location = location or "India"
        
        url = (
            f"{self.SEARCH_URL}?"
            f"q={query}"
            f"&l={location}"
            f"&sort=date"
            f"&exp=entry"
            f"&jt=fulltime"
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
            print(f"Indeed scrape error: {e}")
        
        return jobs[:max_results]
    
    def _parse_jobs(self, html: str) -> List[ScrapedJob]:
        """Parse Indeed job listings."""
        soup = self._parse_html(html)
        jobs = []
        
        job_cards = soup.select('div.jobSEARCH -result')
        if not job_cards:
            job_cards = soup.select('div.job-card')
        if not job_cards:
            job_cards = soup.select('div[data-testid="job-search-results"] li')
        
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
            card.select_one('h2.jobTitle') or
            card.select_one('a.jobTitle') or
            card.select_one('[class*="title"]') or
            card.select_one('span[class*="title"]')
        )
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        link_elem = (
            card.select_one('a.jobTitle') or
            card.select_one('a[class*="job"]') or
            card.select_one('a[href*="/jobs/view"]')
        )
        
        url = ""
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
        
        company_elem = (
            card.select_one('span.companyName') or
            card.select_one('div.company') or
            card.select_one('[class*="company"]')
        )
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
        
        location_elem = (
            card.select_one('div.companyLocation') or
            card.select_one('div.location') or
            card.select_one('[class*="location"]')
        )
        location = location_elem.get_text(strip=True) if location_elem else "Unknown"
        
        time_elem = (
            card.select_one('span.date') or
            card.select_one('div[data-testid="myJobDerivedPagination"]') or
            card.select_one('[class*="date"]')
        )
        posted_time = time_elem.get_text(strip=True) if time_elem else None
        
        salary_elem = (
            card.select_one('div.salary-snippet') or
            card.select_one('[class*="salary"]')
        )
        salary = salary_elem.get_text(strip=True) if salary_elem else None
        
        return ScrapedJob(
            title=title,
            company=company,
            location=location,
            url=url,
            posted_time=posted_time,
            salary=salary,
            source="indeed"
        )
    
    def get_source_name(self) -> str:
        return "indeed"


async def scrape_indeed_jobs(
    keywords: List[str],
    location: Optional[str] = None,
    max_results: int = 20
) -> List[ScrapedJob]:
    """Convenience function."""
    async with IndeedScraper(headless=True) as scraper:
        return await scraper.scrape(keywords, location, max_results)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        async with IndeedScraper(headless=False) as scraper:
            jobs = await scraper.scrape(["python", "developer"], "India", 5)
            for job in jobs:
                print(f"- {job.title} at {job.company}")
    
    asyncio.run(test())
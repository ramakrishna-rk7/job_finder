"""Google Jobs scraper - Safe fallback source."""

import re
from typing import List, Optional

from .base import BaseScraper, ScrapedJob
from ...utils.time_utils import parse_google_jobs_time


class GoogleJobsScraper(BaseScraper):
    """Google Jobs scraper - aggregates from multiple sources."""
    
    BASE_URL = "https://jobs.google.com"
    SEARCH_URL = "https://www.google.com/search"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """Scrape jobs from Google Jobs."""
        query = " ".join(keywords)
        location = location or "India"
        
        url = (
            f"{self.SEARCH_URL}?"
            f"q={query}+jobs"
            f"&l={location}"
            f"&tbs=qdr:d"  # Past 24 hours
            f"&tbm=nws"  # News/jobs
        )
        
        jobs = []
        
        try:
            async with (await self.new_page()) as page:
                await page.goto(url, wait_until="domcontentloaded")
                await self._human_delay()
                await self._scroll_page(page, scrolls=2)
                
                html = await page.content()
                jobs = self._parse_jobs(html)
        except Exception as e:
            print(f"Google Jobs scrape error: {e}")
        
        return jobs[:max_results]
    
    def _parse_jobs(self, html: str) -> List[ScrapedJob]:
        """Parse Google job listings."""
        soup = self._parse_html(html)
        jobs = []
        
        job_cards = soup.select('div.jobSEARCH -result')
        if not job_cards:
            job_cards = soup.select('li.ogTdqe')
        
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
            card.select_one('h3') or
            card.select_one('[class*="title"]') or
            card.select_one('[role="heading"]')
        )
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        if not title:
            return None
        
        link_elem = card.select_one('a')
        url = ""
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            if href.startswith('/url'):
                match = re.search(r'q=([^&]+)', href)
                if match:
                    from urllib.parse import unquote
                    url = unquote(match.group(1))
            elif href.startswith('http'):
                url = href
        
        company_elem = (
            card.select_one('div.company') or
            card.select_one('[class*="company"]') or
            card.select_one('span.sub')
        )
        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
        
        location_elem = (
            card.select_one('div.location') or
            card.select_one('[class*="location"]')
        )
        location = location_elem.get_text(strip=True) if location_elem else "Unknown"
        
        time_elem = (
            card.select_one('span.date') or
            card.select_one('[class*="date"]')
        )
        posted_time = time_elem.get_text(strip=True) if time_elem else "Today"
        
        return ScrapedJob(
            title=title,
            company=company,
            location=location,
            url=url,
            posted_time=posted_time,
            source="google_jobs"
        )
    
    def get_source_name(self) -> str:
        return "google_jobs"


async def scrape_google_jobs(
    keywords: List[str],
    location: Optional[str] = None,
    max_results: int = 20
) -> List[ScrapedJob]:
    """Convenience function."""
    async with GoogleJobsScraper(headless=True) as scraper:
        return await scraper.scrape(keywords, location, max_results)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        async with GoogleJobsScraper(headless=False) as scraper:
            jobs = await scraper.scrape(["python", "developer"], "India", 5)
            for job in jobs:
                print(f"- {job.title} at {job.company}")
    
    asyncio.run(test())
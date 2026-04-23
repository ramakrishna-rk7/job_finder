"""LinkedIn scraper - Indirect via Google search results."""

import re
from typing import List, Optional

from .base import BaseScraper, ScrapedJob


class LinkedInScraper(BaseScraper):
    """LinkedIn job scraper - indirect via Google.
    
    Since LinkedIn has strong anti-bot protection, we use Google search
    to find LinkedIn job listings indirectly.
    """
    
    BASE_URL = "https://www.linkedin.com"
    JOB_SEARCH_URL = "https://www.linkedin.com/jobs/search"
    
    def __init__(self, **kwargs):
        kwargs['use_stealth'] = kwargs.get('use_stealth', True)
        super().__init__(**kwargs)
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """Scrape LinkedIn jobs via Google search."""
        query = " ".join(keywords)
        location = location or "India"
        
        google_url = (
            f"https://www.google.com/search?"
            f"q={query}+jobs+linkedin+{location}"
            f"&tbs=qdr:d"  # Past 24 hours
            f"&tbm=nws"  # News
        )
        
        jobs = []
        
        try:
            async with (await self.new_page()) as page:
                await page.goto(google_url, wait_until="domcontentloaded")
                await self._human_delay()
                await self._scroll_page(page, scrolls=2)
                
                html = await page.content()
                jobs = self._parse_google_links(html)
        except Exception as e:
            print(f"LinkedIn (via Google) scrape error: {e}")
        
        return jobs[:max_results]
    
    def _parse_google_links(self, html: str) -> List[ScrapedJob]:
        """Parse Google search results for LinkedIn links."""
        soup = self._parse_html(html)
        jobs = []
        
        result_divs = soup.select('div.SnsPEV')
        
        for div in result_divs:
            try:
                link = div.select_one('a[href*="linkedin.com/jobs/view"]')
                if not link:
                    continue
                
                url = link.get('href', '')
                if not url or 'linkedin.com/jobs' not in url:
                    continue
                
                title_elem = div.select_one('div.mCBk')
                title = title_elem.get_text(strip=True) if title_elem else "LinkedIn Job"
                
                company_elem = div.select_one('div[role="heading"]')
                company = company_elem.get_text(strip=True) if company_elem else "Company"
                
                snippet = div.select_one('div[id="web"]')
                location = ""
                if snippet:
                    text = snippet.get_text(strip=True)
                    loc_match = re.search(r'([A-Z][a-z]+,\s*[A-Z]{2}|[A-Z][a-z]+)', text)
                    if loc_match:
                        location = loc_match.group(1)
                
                if not location:
                    location = "Remote"
                
                job = ScrapedJob(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    posted_time="Today",
                    source="linkedin"
                )
                jobs.append(job)
            except Exception:
                continue
        
        return jobs
    
    def get_source_name(self) -> str:
        return "linkedin"


async def scrape_linkedin_jobs(
    keywords: List[str],
    location: Optional[str] = None,
    max_results: int = 20
) -> List[ScrapedJob]:
    """Convenience function."""
    async with LinkedInScraper(headless=True) as scraper:
        return await scraper.scrape(keywords, location, max_results)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        async with LinkedInScraper(headless=False) as scraper:
            jobs = await scraper.scrape(["python", "developer"], "India", 5)
            for job in jobs:
                print(f"- {job.title} at {job.company}")
    
    asyncio.run(test())
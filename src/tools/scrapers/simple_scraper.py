"""Simple HTTP-based job scraper using httpx."""

import re
import asyncio
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup

from ...schemas.models import JobListing, StructuredQuery
from ...utils.time_utils import extract_hours, normalize_posted_time


class SimpleJobScraper:
    """Simple HTTP-based job scraper."""
    
    SOURCE = "indeed"
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[JobListing]:
        """Scrape jobs from Indeed."""
        query = "+".join(keywords)
        location = location or "India"
        
        urls = [
            f"https://www.indeed.com/jobs?q={query}&l={location}&sort=date&exp=entry",
            f"https://www.indeed.com/jobs?q={query}&l={location}&sort=date",
        ]
        
        all_jobs = []
        
        for url in urls[:1]:
            try:
                response = await self.session.get(url)
                if response.status_code == 200:
                    jobs = self._parse_indeed(response.text)
                    all_jobs.extend(jobs)
            except Exception as e:
                print(f"Scraping error: {e}")
                continue
        
        return all_jobs[:max_results]
    
    def _parse_indeed(self, html: str) -> List[JobListing]:
        """Parse Indeed job listings."""
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        job_cards = soup.find_all('div', class_=re.compile('jobsearch-ResultsContainer|job-card|jobtitle'))
        
        if not job_cards:
            job_cards = soup.find_all('li', class_=re.compile('jobsearch-ResultsContainer'))
        
        for card in job_cards[:15]:
            try:
                title_elem = card.find('h2') or card.find('a', class_=re.compile('jobtitle'))
                title = title_elem.get_text(strip=True) if title_elem else None
                
                if not title or 'job' not in title.lower():
                    continue
                
                link_elem = card.find('a', href=re.compile(r'/jobs/view|/company'))
                url = ""
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    url = f"https://www.indeed.com{href}" if href.startswith('/') else href
                
                company_elem = card.find('span', class_=re.compile('company')) or card.find('div', class_=re.compile('company'))
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                location_elem = card.find('div', class_=re.compile('companyLocation|location')) or card.find('span', class_=re.compile('location'))
                location = location_elem.get_text(strip=True) if location_elem else "Unknown"
                
                date_elem = card.find('span', class_=re.compile('date|dateAgo')) or card.find('div', class_=re.compile('date'))
                posted_time = date_elem.get_text(strip=True) if date_elem else "Today"
                
                if title and url:
                    jobs.append(JobListing(
                        title=title,
                        company=company,
                        location=location,
                        url=url,
                        posted_time=normalize_posted_time(posted_time),
                        source=self.SOURCE
                    ))
            except Exception:
                continue
        
        return jobs


async def scrape_simple_jobs(
    keywords: List[str],
    location: Optional[str] = None,
    max_results: int = 20
) -> List[JobListing]:
    """Convenience function."""
    async with SimpleJobScraper() as scraper:
        return await scraper.scrape(keywords, location, max_results)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        jobs = await scrape_simple_jobs(["python", "developer"], "India", 5)
        for job in jobs:
            print(f"- {job.title} @ {job.company}")
            print(f"  {job.posted_time} | {job.url}")
    
    asyncio.run(test())
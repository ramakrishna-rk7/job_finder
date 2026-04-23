"""Simple URL-based job scraper - fallback when Playwright fails."""

import re
from typing import List, Optional
import httpx

from ...schemas.models import JobListing, StructuredQuery
from ...utils.time_utils import normalize_posted_time


class URLJobScraper:
    """Simple URL generation scraper - generates job search URLs."""
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[JobListing]:
        """Generate job search URLs."""
        keywords_str = "-".join(keywords)
        location = location or "India"
        
        sources = [
            ("Indeed", f"https://www.indeed.com/jobs?q={keywords_str}&l={location}&sort=date"),
            ("Naukri", f"https://www.naukri.com/jobs?q={keywords_str}&l={location}"),
            ("LinkedIn", f"https://www.linkedin.com/jobs/search/?keywords={keywords_str}&location={location}"),
            ("Google Jobs", f"https://www.google.com/search?q={keywords_str}+jobs+{location}"),
        ]
        
        jobs = []
        for source_name, url in sources:
            jobs.append(JobListing(
                title=f"{' '.join(keywords).title()} - {source_name} Jobs",
                company=source_name,
                location=location,
                url=url,
                posted_time="Today",
                posted_date=None,
                source=source_name.lower()
            ))
        
        return jobs[:max_results]


class HTTPJobScraper:
    """HTTP-based job scraper without Playwright."""
    
    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()
    
    async def scrape_indeed(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 10
    ) -> List[JobListing]:
        """Scrape Indeed via HTTP."""
        query = "-".join(keywords)
        location = location or "India"
        url = f"https://www.indeed.com/jobs?q={query}&l={location}"
        
        try:
            response = await self.session.get(url)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                jobs = []
                results = soup.find_all('div', class_=re.compile('jobsearch-ResultsContainer'))
                
                for item in results[:max_results]:
                    title_elem = item.find('h2')
                    if not title_elem:
                        title_elem = item.find('a', class_=re.compile('jobtitle'))
                    
                    link_elem = item.find('a', href=re.compile(r'/company|/jobs'))
                    company_elem = item.find('span', class_=re.compile('company'))
                    location_elem = item.find('div', class_=re.compile('companyLocation'))
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        href = link_elem.get('href') if link_elem else ""
                        job_url = f"https://www.indeed.com{href}" if href.startswith('/') else href
                        company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                        loc = location_elem.get_text(strip=True) if location_elem else location
                        
                        jobs.append(JobListing(
                            title=title,
                            company=company,
                            location=loc,
                            url=job_url,
                            posted_time="Today",
                            source="indeed"
                        ))
                
                return jobs
        except Exception as e:
            print(f"HTTP scrape error: {e}")
        
        return []


async def scrape_jobs_http(
    keywords: List[str],
    location: Optional[str] = None,
    max_results: int = 20
) -> List[JobListing]:
    """Convenience function."""
    async with HTTPJobScraper() as scraper:
        jobs = await scraper.scrape_indeed(keywords, location, max_results)
        if not jobs:
            async with URLJobScraper() as fallback:
                jobs = await fallback.scrape(keywords, location, max_results)
        return jobs


if __name__ == "__main__":
    import asyncio
    jobs = asyncio.run(scrape_jobs_http(["python", "developer"], "India", 5))
    for job in jobs:
        print(f"- {job.title}")
        print(f"  {job.url}")
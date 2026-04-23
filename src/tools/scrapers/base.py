"""Base scraper with Playwright and deduplication."""

import asyncio
import random
import re
from abc import ABC, abstractmethod
from typing import List, Optional, Set
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Browser, Page, Playwright
from bs4 import BeautifulSoup

from ...schemas.models import JobListing
from ...utils.time_utils import extract_hours, normalize_posted_time


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]


@dataclass
class ScrapedJob:
    """Internal job representation before normalization."""
    title: str
    company: str
    location: str
    url: str
    posted_time: Optional[str] = None
    description: Optional[str] = None
    salary: Optional[str] = None
    source: str = "unknown"


class DeduplicationEngine:
    """Deduplicate jobs by URL and title similarity."""
    
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_titles: Set[str] = set()
    
    def is_duplicate(self, job: ScrapedJob) -> bool:
        """Check if job is duplicate."""
        if job.url and job.url in self.seen_urls:
            return True
        
        normalized_title = self._normalize_title(job.title)
        if normalized_title in self.seen_titles:
            return True
        
        return False
    
    def add(self, job: ScrapedJob):
        """Mark job as seen."""
        if job.url:
            self.seen_urls.add(job.url)
        normalized_title = self._normalize_title(job.title)
        self.seen_titles.add(normalized_title)
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        return re.sub(r'[^a-z0-9]', '', title.lower())
    
    def reset(self):
        """Reset deduplication state."""
        self.seen_urls.clear()
        self.seen_titles.clear()


class BaseScraper(ABC):
    """Abstract base scraper with Playwright support."""
    
    def __init__(
        self,
        headless: bool = True,
        use_stealth: bool = True,
        min_delay: float = 0.5,
        max_delay: float = 1.5
    ):
        self.headless = headless
        self.use_stealth = use_stealth
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.browser: Optional[Browser] = None
        self.playwright: Optional[Playwright] = None
        self.dedup = DeduplicationEngine()
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Initialize Playwright and browser."""
        self.playwright = await async_playwright().start()
        
        if self.use_stealth:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
        else:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless
            )
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def new_page(self) -> Page:
        """Create new page with stealth settings."""
        page = await self.browser.new_page()
        
        if self.use_stealth:
            await page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
            })
        
        await page.set_default_timeout(30000)
        return page
    
    def _random_delay(self) -> float:
        """Get random delay for human-like behavior."""
        return random.uniform(self.min_delay, self.max_delay)
    
    async def _human_delay(self):
        """Human-like delay between actions."""
        await asyncio.sleep(self._random_delay())
    
    async def _scroll_page(self, page: Page, scrolls: int = 2):
        """Scroll page to load dynamic content."""
        for _ in range(scrolls):
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(0.3)
    
    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML with BeautifulSoup."""
        return BeautifulSoup(html, 'html.parser')
    
    @abstractmethod
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """Scrape jobs - to be implemented by subclasses."""
        pass
    
    async def scrape_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[JobListing]:
        """Scrape and convert to JobListing."""
        scraped = await self.scrape(keywords, location, max_results)
        
        jobs = []
        for sjob in scraped:
            if self.dedup.is_duplicate(sjob):
                continue
            
            self.dedup.add(sjob)
            
            hours = extract_hours(sjob.posted_time) if sjob.posted_time else 999
            
            job = JobListing(
                title=sjob.title,
                company=sjob.company,
                location=sjob.location,
                url=sjob.url,
                description=sjob.description,
                salary=sjob.salary,
                posted_time=normalize_posted_time(sjob.posted_time) if sjob.posted_time else None,
                source=self.get_source_name()
            )
            jobs.append(job)
        
        return jobs
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return source name."""
        pass
    
    def _clean_text(self, text: Optional[str]) -> str:
        """Clean text content."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        match = re.search(r'https?://([^/]+)', url)
        if match:
            domain = match.group(1)
            return domain.split('.')[-2] if '.' in domain else domain
        return "unknown"


class SimpleScraper(BaseScraper):
    """Simple HTTP-based scraper (fallback)."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        max_results: int = 20
    ) -> List[ScrapedJob]:
        """Scrape using HTTP requests (fallback)."""
        import httpx
        
        query = " ".join(keywords)
        location = location or "India"
        
        urls = self._build_urls(query, location)
        
        jobs = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in urls[:3]:
                try:
                    response = await client.get(url, headers={'User-Agent': random.choice(USER_AGENTS)})
                    if response.status_code == 200:
                        jobs.extend(self._parse_response(response.text))
                except Exception:
                    continue
        
        return jobs[:max_results]
    
    def _build_urls(self, query: str, location: str) -> List[str]:
        """Build search URLs."""
        return []
    
    def _parse_response(self, html: str) -> List[ScrapedJob]:
        """Parse HTML response."""
        return []
    
    def get_source_name(self) -> str:
        return "unknown"
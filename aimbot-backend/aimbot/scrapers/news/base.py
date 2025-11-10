from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import aiohttp
import random
import time
import asyncio
import logging

from bs4 import BeautifulSoup
from aiolimiter import AsyncLimiter

from aimbot.scrapers.config import HEADERS
from aimbot.models.news import NewsStory, FamilyNotice

logger = logging.getLogger(__name__)

@dataclass
class ScraperResponse:
    """Dataclass to hold scraper response data"""
    url: str
    soup: BeautifulSoup

class BaseScraper(ABC):
    """Base class for all news scrapers"""

    # mapping of news sections to URLs to extract story links from
    # i.e. 
    # {
    #   "news" : "https://example.com/news",
    #   "sports": "https://example.com/sports"
    # }
    sections: dict[str, str]
    limiter = AsyncLimiter(max_rate=5, time_period=2) # 5 requests every 2 seconds
    
    def __init__(self):
        raise NotImplementedError("BaseScraper is an abstract class and cannot be instantiated directly")

    @property
    def available_sections(self) -> List[str]:
        """Return a list of available sections for this scraper"""
        return list(self.sections.keys())

    def parse(self, soup: BeautifulSoup) -> NewsStory:
        """Parse the BeautifulSoup object to extract data"""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def fetch(self, url: str) -> ScraperResponse:
        """Fetch and parse a web page"""
        # Add random query parameter to prevent caching
        separator = '&' if '?' in url else '?'
        cache_buster = f"{separator}_t={int(time.time())}&_r={random.randint(1000, 9999)}"
        url_with_cache_buster = f"{url}{cache_buster}"
        
        async with self.limiter:
            async with aiohttp.ClientSession() as client:
                async with client.get(url_with_cache_buster, headers=HEADERS) as response:
                    response.raise_for_status()
                    return ScraperResponse(url=url, soup=BeautifulSoup(await response.text(), 'html.parser'))
                
    async def fetch_all(self, urls: List[str]) -> List[ScraperResponse]:
        """Fetch multiple URLs concurrently"""
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def get_story_urls(self, section: str, limit: Optional[int] = None) -> list[str]:
        """Get a list of news story URLs for given section"""
        raise NotImplementedError("Subclasses must implement this method")
    
    async def fetch_n_stories_for_section(self, section: str, limit: int = 10) -> list[NewsStory]:
        """Fetch and parse news stories for a given section"""
        logger.debug(f"fetch_n_stories_for_section called for section '{section}' with limit {limit}")
        urls = await self.get_story_urls(section, limit)
        logger.debug(f"Got {len(urls)} URLs to fetch")
        responses = await self.fetch_all(urls)
        logger.debug(f"Fetched {len(responses)} responses")
        stories = []
        for response in responses:
            try:
                story = self.parse(response)
                stories.append(story)
            except Exception as e:
                logger.error(f"Failed to parse story from {response.url}: {e}", exc_info=True)
        logger.debug(f"Successfully parsed {len(stories)} stories out of {len(responses)} responses")
        return stories

    async def fetch_n_stories_for_all_sections(self, limit_per_section: int = 10) -> dict[str, list[NewsStory]]:
        tasks = []
        for section in self.sections.keys():
            tasks.append(self.fetch_n_stories_for_section(section, limit_per_section))
        results = await asyncio.gather(*tasks)
        # return dict
        return {section: stories for section, stories in zip(self.sections.keys(), results)}


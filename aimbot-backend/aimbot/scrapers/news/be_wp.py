from abc import ABC, abstractmethod
import logging
from dateutil.parser import parse as date_parse
from typing import Optional
import time
import random

from bs4 import BeautifulSoup
import aiohttp

from aimbot.scrapers.config import HEADERS
from aimbot.scrapers.news.base import BaseScraper, ScraperResponse
from aimbot.models.news import NewsStory

class BEWordpress(BaseScraper):
    """BE Scraper for BE Jersey using the wordpress endpoints"""

    # sections here are a mapping from section name to wordpress category
    sections: dict[str, str] = {
        "news": "2",
        "business": "53",
        "sport": "39",
        "opinion": "314",
        "community": "164",
        "podcasts": None # I cant find a podcast category in the endpoint
    }

    def __init__(self):
        pass

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
                    return await response.json()

    async def fetch_n_stories_for_section(self, section: str, limit: int = 10) -> list[NewsStory]:
        """
        This is an override of the base method as we don't need the same approach the other
        scrapers use.
        """
        section_id = self.sections.get(section)
        if section_id is None:
            return [] # no category for this section so just return empty list
        response = await self.fetch(f"https://www.bailiwickexpress.com/wp-json/wp/v2/posts?per_page={limit}&categories={section_id}")
        stories = []
        for post in response:
            # get headline
            title = post.get('title')
            if title and title.get('rendered'):
                title_soup = BeautifulSoup(title.get('rendered'), 'html.parser')
                title = title_soup.get_text(strip=True)
            else:
                title = ""
            # get article text
            text = ""
            content = post.get('content')
            if content and content.get('rendered'):
                soup = BeautifulSoup(content.get('rendered'), 'html.parser')
                text = "\n".join([p.text for p in soup.find_all('p')])
            else:
                text = ""
            # get date
            try:
                date = date_parse(post.get('date'))
            except Exception as e:
                date = None
            # get author
            yoast = post.get('yoast_head_json')
            if yoast and yoast.get('author'):
                author = yoast.get('author')
            else:
                author = ""
            # get image url
            image_url = post.get('jetpack_featured_media_url') or ""
            # append story
            stories.append(NewsStory(
                headline=title,
                text=text,
                author=author,
                url = post.get('link') or "",
                image_url=image_url,
                date=date,
            ))
        return stories

if __name__ == "__main__":
    import asyncio
    async def main():
        scraper = BEWordpress()
        # authors = await scraper.get_authors()
        stories = await scraper.fetch_n_stories_for_all_sections(limit_per_section=10)
    asyncio.run(main())


from abc import ABC, abstractmethod
import logging
from dateutil.parser import parse as date_parse
from typing import Optional

from bs4 import BeautifulSoup

from aimbot.scrapers.news.base import BaseScraper, ScraperResponse
from aimbot.models.news import NewsStory

logger = logging.getLogger(__name__)

class JEPScraper(BaseScraper):
    """Scraper for Jersey Evening Post"""

    sections: dict[str, str] = {
        "news": "https://jerseyeveningpost.com/category/news/",
        "premium": "https://jerseyeveningpost.com/tag/premium/"
    }

    def __init__(self):
        pass

    def parse(self, response: ScraperResponse) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        soup = response.soup
        # get headline
        headline = soup.find('h1', class_='entry-title').text.strip()
        # get article text
        entry_content = soup.find('div', class_='entry-content')
        p_tags = entry_content.find_all('p')
        text = '\n'.join([p.text.strip() for p in p_tags])
        # capitalize first word of text, JEP defaults to all caps first word
        words = text.split()
        if words[0].lower() == 'a':
            words[0] = words[0].capitalize()
            words[1] = words[1].lower()
        else:
            words[0] = words[0].capitalize()
        text = ' '.join(words)
        # get date
        date = soup.find('time').text
        try:
            date = date_parse(date)
        except:
            date = None
        # get author
        author = soup.find('span', class_='byline').text or "Jersey Evening Post"
        author = author.replace('\n', ' ').strip()
        if author.lower().startswith("by "):
            author = author[3:]
        # get image url
        try:
            image_url = soup.find('figure', class_='post-thumbnail').find('img').get('src')
        except Exception as e:
            logger.debug(f"Failed to get image url for {soup.url}")
            image_url = None
        return NewsStory(
            headline=headline,
            text=text,
            date=date,
            author=author,
            url=response.url,
            image_url=image_url
        )

    async def get_story_urls(self, section: str, limit: Optional[int] = None) -> list[str]:
        """
        Get a list of news story URLs from the Jersey Evening Post homepage.
        """
        limit = limit or float('inf')
        homepage_url = self.sections.get(section)
        if not homepage_url:
            raise ValueError(f"Section '{section}' not recognised, available sections are {list(self.sections.keys())}")
        response = await self.fetch(homepage_url)
        soup = response.soup
        titles = soup.find_all('h2', class_='entry-title')
        news_urls = []
        for title in titles:
            link = title.find('a').get('href')
            if link:
                news_urls.append(link)
        return news_urls
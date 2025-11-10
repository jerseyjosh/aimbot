from abc import ABC, abstractmethod
import logging
from dateutil.parser import parse as date_parse
from typing import Optional

from bs4 import BeautifulSoup

from aimbot.scrapers.news.base import BaseScraper, ScraperResponse
from aimbot.models.news import NewsStory

logger = logging.getLogger(__name__)

class BEScraper(BaseScraper):
    """Scraper for Bailiwick Express Jersey"""

    sections: dict[str, str] = {
        "news": "https://www.bailiwickexpress.com/news/",
        "business": "https://www.bailiwickexpress.com/jsy-business/",
        "sport": "https://www.bailiwickexpress.com/jsy-sport/",
        "opinion": "https://www.bailiwickexpress.com/opinion-jersey/",
        "community": "https://www.bailiwickexpress.com/jsy-community/",
        "podcasts": "https://www.bailiwickexpress.com/jsy-radio-podcasts/"
    }

    def __init__(self):
        pass

    def parse(self, response: ScraperResponse) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        logger.debug(f"Parsing story from {response.url}")
        # get headline
        soup = response.soup
        headline = soup.find('h1').text.strip()
        logger.debug(f"Found headline: {headline}")
        # get article text
        entry_content = soup.find('div', class_='entry-content')
        p_tags = entry_content.find_all('p')
        text = '\n'.join([p.text.strip() for p in p_tags])
        logger.debug(f"Extracted {len(p_tags)} paragraphs, total length: {len(text)} chars")
        # get date
        date = soup.find('time').text
        try:
            date = date_parse(date).date()
            logger.debug(f"Parsed date: {date}")
        except Exception as e:
            logger.warning(f"Failed to parse date '{date}': {e}")
            date = None
        # get author
        author = soup.find('a', class_=['url', 'fn', 'a'])
        if author is not None:
            author = author.text.strip()
        else:
            author = "Bailiwick Express"
        logger.debug(f"Found author: {author}")
        # get image url
        try:
            image_url = soup.find('figure', class_='post-thumbnail').find('img').get('src')
            image_url = image_url.split('?')[0] # remove query string
            logger.debug(f"Found image URL: {image_url}")
        except Exception as e:
            logger.debug(f"Failed to get image url for {response.url}: {e}")
            image_url = None

        logger.debug(f"Successfully parsed story: {headline}")
        return NewsStory(
            headline=headline,
            text=text,
            author=author,
            url=response.url,
            image_url=image_url,
            date = date
        )

    async def get_story_urls(self, section: str, limit: Optional[int] = None) -> list[str]:
        """
        Get a list of news story URLs from the Bailiwick Express homepage.
        """
        logger.debug(f"Fetching story URLs for section: {section}")
        limit = limit or float('inf')
        homepage_url = self.sections.get(section)
        if not homepage_url:
            raise ValueError(f"Section '{section}' not recognised, available sections are {list(self.sections.keys())}")
        logger.debug(f"Fetching homepage: {homepage_url}")
        response = await self.fetch(homepage_url)
        soup = response.soup
        articles = soup.find_all('article')
        logger.debug(f"Found {len(articles)} articles on homepage")
        urls = []
        for article in articles:
            a_tag = article.find('a', href=True)
            if a_tag and a_tag['href'] not in urls:
                urls.append(a_tag['href'])
            if len(urls) >= limit:
                break
        logger.debug(f"Extracted {len(urls)} unique story URLs")
        return urls
    
if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    
    import asyncio
    async def test():
        scraper = BEScraper()
        results = await scraper.fetch_n_stories_for_section('sport')
        for story in results:
            print(f"Headline: {story.headline}")
            print(f"Author: {story.author}")
            print(f"URL: {story.url}")
            print(f"Text: {story.text[:100]}...")  # Print first 100 characters
            print(f"Image URL: {story.image_url}")
            print("-" * 40)

    asyncio.run(test())
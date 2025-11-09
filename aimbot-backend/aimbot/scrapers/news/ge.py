from abc import ABC, abstractmethod
import logging
from dateutil.parser import parse as date_parse
from typing import Optional

from bs4 import BeautifulSoup

from aimbot.scrapers.news.base import BaseScraper, ScraperResponse
from aimbot.models.news import NewsStory

logger = logging.getLogger(__name__)

class GEScraper(BaseScraper):
    """Scraper for Bailiwick Express Guernsey"""

    sections: dict[str, str] = {
        "news": "https://www.bailiwickexpress.com/bailiwickexpress-guernsey-edition/",
        "business": "https://www.bailiwickexpress.com/gsy-business/",
        "sport": "https://www.bailiwickexpress.com/gsy-sport/",
        "opinion": "https://www.bailiwickexpress.com/opinion-guernsey/",
        "community": "https://www.bailiwickexpress.com/gsy-community/",
        "podcasts": "https://www.bailiwickexpress.com/jsy-radio-podcasts/"
    }

    def __init__(self):
        super().__init__()

    def parse(self, response: ScraperResponse) -> NewsStory:
        """
        Parse a news story from the given url.
        """
        # get headline
        soup = response.soup
        headline = soup.find('h1').text.strip()
        # get article text
        entry_content = soup.find('div', class_='entry-content')
        p_tags = entry_content.find_all('p')
        text = '\n'.join([p.text.strip() for p in p_tags])
        # get date
        date = soup.find('time').text
        try:
            date = date_parse(date).date()
        except Exception as e:
            date = None
        # get author
        author = soup.find('a', class_=['url', 'fn', 'a'])
        if author is not None:
            author = author.text.strip()
        else:
            author = "Bailiwick Express"
        # get image url
        try:
            image_url = soup.find('figure', class_='post-thumbnail').find('img').get('src')
            image_url = image_url.split('?')[0] # remove query string
        except Exception as e:
            logger.debug(f"Failed to get image url for {response.url}")
            image_url = None

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
        limit = limit or float('inf')
        homepage_url = self.sections.get(section)
        if not homepage_url:
            raise ValueError(f"Section '{section}' not recognised, available sections are {list(self.sections.keys())}")
        response = await self.fetch(homepage_url)
        soup = response.soup
        articles = soup.find_all('article')
        urls = []
        for article in articles:
            a_tag = article.find('a', href=True)
            if a_tag and a_tag['href'] not in urls:
                urls.append(a_tag['href'])
            if len(urls) >= limit:
                break
        return urls
    
if __name__ == "__main__":
    
    import asyncio
    async def test():
        scraper = GEScraper()
        results = await scraper.fetch_n_stories_for_section('sport')
        for story in results:
            print(f"Headline: {story.headline}")
            print(f"Author: {story.author}")
            print(f"URL: {story.url}")
            print(f"Text: {story.text[:100]}...")  # Print first 100 characters
            print(f"Image URL: {story.image_url}")
            print("-" * 40)

        # urls = await scraper.get_story_urls(section = "sporting", limit=3)
        # responses = await scraper.fetch_all(urls)
        # for response in responses:
        #     story = scraper.parse(response)
        #     print(f"Headline: {story.headline}")
        #     print(f"Author: {story.author}")
        #     print(f"URL: {story.url}")
        #     print(f"Text: {story.text[:100]}...")  # Print first 100 characters
        #     print(f"Image URL: {story.image_url}")
        #     print("-" * 40)
    
    asyncio.run(test())
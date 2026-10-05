import logging
import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from unittest import result

from bs4 import BeautifulSoup
from bs4.element import Tag

from aimbot.scrapers.config import create_client_session

logger = logging.getLogger(__name__)

class WeatherRegion(Enum):
    # region = (weather_url tides_url)
    JSY = ("https://www.bbc.co.uk/weather/3042091", "https://www.bbc.co.uk/weather/coast-and-sea/tide-tables/10/1605")
    GSY = ("https://www.bbc.co.uk/weather/6296594", "https://www.bbc.co.uk/weather/coast-and-sea/tide-tables/10/1604")

@dataclass
class WeatherResponse:
    weather: str # description of weather
    tides: str # description of tides

class WeatherScraper:

    def __init__(self, region: WeatherRegion):
        self.region = region

    @classmethod
    def Jsy(cls):
        return cls(region=WeatherRegion.JSY)
    
    @classmethod
    def Gsy(cls):
        return cls(region=WeatherRegion.GSY)

    @staticmethod
    def parse_tides(soup: BeautifulSoup) -> str:
        """Build the tide summary from a BBC tide-table page.

        The tide type (High/Low) is the first data cell of each row; the table
        header and any layout rows only use ``<th>`` and are skipped. Rows such
        as "Current tide" carry a type that is neither High nor Low and are
        intentionally ignored.
        """
        low_tides = []
        high_tides = []
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            tide_type = cells[0].get_text(" ", strip=True).lower()
            time_match = re.match(r'\d{1,2}:\d{2}', cells[1].get_text(" ", strip=True))
            if not time_match:
                continue
            time = datetime.strptime(time_match.group(0), "%H:%M").strftime("%I:%M %p")
            if tide_type == 'low':
                low_tides.append(time)
            elif tide_type == 'high':
                high_tides.append(time)
        return f"Low tides at {', '.join(low_tides)}, with high tides at {', '.join(high_tides)}".strip()

    async def get_weather(self) -> WeatherResponse:
        """Fetch the weather and tides from BBC"""
        # extract urls
        weather_url, tides_url = self.region.value
        
        async with create_client_session() as session:
            # Get weather
            async with session.get(weather_url) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                try:
                    weather = soup.find('div', class_=['ssrcss-1cxacys-TextContent e18m38lv2']).find_all('p')[1].text
                except Exception as e:
                    logger.error(f"Error parsing weather: {e}")
                    weather = ""
            
            # Get tides
            async with session.get(tides_url) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')
                tides = self.parse_tides(soup)
        
        return WeatherResponse(
            weather=weather.strip(),
            tides=tides.strip()
        )


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('websockets').setLevel(logging.ERROR)
    
    async def main():
        scraper = WeatherScraper.Gsy()
        response = await scraper.get_weather()
        print(response.weather)
        print(response.tides)

    import asyncio
    asyncio.run(main())
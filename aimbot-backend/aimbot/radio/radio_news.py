import logging
import asyncio
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from elevenlabs import ElevenLabs

from aimbot.models.news import NewsStory
from aimbot.models.radio import RadioNewsData

from aimbot.scrapers.news.be import BEScraper
from aimbot.scrapers.news.ge import GEScraper
from aimbot.scrapers.weather import WeatherScraper

logger = logging.getLogger(__name__)

class RadioNews:

    NUM_SENTENCES_PER_STORY = 1
    NUM_STORIES_PER_REGION = 2

    def __init__(self, speaker: str):
        self.speaker = speaker
        self.jsy_scraper = BEScraper()
        self.gsy_scraper = GEScraper()
        self.weather_scraper = WeatherScraper.Jsy()
        self.elabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        logger.info(f"DailyNews initialized with speaker: {speaker}")

    @staticmethod
    def elevenlabs_to_name(speaker: str) -> str:
        if 'christie' in speaker:
            return "Christie Bailey"
        elif 'jodie' in speaker:
            return "Jodie Yettram"
        elif 'fiona' in speaker:
            return "Fiona Potigny"
        else:
            raise ValueError(f"Speaker {speaker} not recognized")
        
    async def get_data(self) -> RadioNewsData:
        logger.info("Fetching all data")
        jsy_stories, gsy_stories, weather_response = await asyncio.gather(
            self.jsy_scraper.fetch_n_stories_for_section("news", limit=self.NUM_STORIES_PER_REGION),
            self.gsy_scraper.fetch_n_stories_for_section("news", limit=self.NUM_STORIES_PER_REGION),
            self.weather_scraper.get_weather()
        )
        logger.info("All data fetched successfully")
        data = RadioNewsData(
            speaker_id = self.speaker,
            stories = jsy_stories + gsy_stories,
            weather = weather_response.weather
        )
        # Set script to generated_script as default
        data.script = data.generated_script
        return data
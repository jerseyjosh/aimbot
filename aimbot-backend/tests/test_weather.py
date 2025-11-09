import pytest
import asyncio

from aimbot.scrapers.weather import WeatherScraper

@pytest.mark.asyncio
async def test_weather_scraper():
    scraper = WeatherScraper.Jsy()
    response = await scraper.get_weather()
    assert response.weather != "", "Weather data should not be empty"
    assert response.tides != "", "Tides data should not be empty"
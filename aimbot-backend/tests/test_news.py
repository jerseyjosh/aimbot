import asyncio
import pytest


@pytest.mark.asyncio
async def test_be_scraper():

    from aimbot.scrapers.news.be import BEScraper

    scraper = BEScraper()
    sections = scraper.available_sections
    tasks = [scraper.fetch_n_stories_for_section(section, limit=5) for section in sections]
    results = await asyncio.gather(*tasks)
    for section, stories in zip(sections, results):
        assert len(stories) > 0, f"No stories fetched for section {section}"


@pytest.mark.asyncio
async def test_ge_scraper():

    from aimbot.scrapers.news.ge import GEScraper

    scraper = GEScraper()
    sections = scraper.available_sections
    tasks = [scraper.fetch_n_stories_for_section(section, limit=5) for section in sections]
    results = await asyncio.gather(*tasks)
    for section, stories in zip(sections, results):
        assert len(stories) > 0, f"No stories fetched for section {section}"

@pytest.mark.asyncio
async def test_jep_scraper():

    from aimbot.scrapers.news.jep import JEPScraper

    scraper = JEPScraper()
    sections = scraper.available_sections
    tasks = [scraper.fetch_n_stories_for_section(section, limit=5) for section in sections]
    results = await asyncio.gather(*tasks)
    for section, stories in zip(sections, results):
        assert len(stories) > 0, f"No stories fetched for section {section}"

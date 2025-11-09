import asyncio
import pytest

@pytest.mark.asyncio
async def test_family_notices_scraper():

    from aimbot.scrapers.family_notices import FamilyNoticesScraper

    scraper = FamilyNoticesScraper()
    notices = await scraper.get_notices()
    assert len(notices) > 0, "No family notices were fetched"
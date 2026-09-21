"""Tests that email fetching degrades gracefully when scrapers fail.

A single failing scraper (e.g. a 429 from a news API) must not cause the whole
endpoint to fail, otherwise the frontend has no email data to edit by hand.
"""
import json

import pytest
from fastapi.testclient import TestClient

import aimbot.main as main


class FailingSectionScraper:
    """Stands in for a news scraper whose requests are being rate limited."""

    def __init__(self, *args, **kwargs):
        pass

    async def fetch_n_stories_for_section(self, *args, **kwargs):
        raise RuntimeError("429 Too Many Requests")


class FailingWeatherScraper:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def Jsy(cls):
        return cls()

    @classmethod
    def Gsy(cls):
        return cls()

    async def get_weather(self):
        raise RuntimeError("429 Too Many Requests")


class FailingFamilyNoticesScraper:
    def __init__(self, *args, **kwargs):
        pass

    async def get_notices(self, *args, **kwargs):
        raise RuntimeError("429 Too Many Requests")


@pytest.fixture
def client(monkeypatch):
    for name in ("BEWordpress", "GEWordpress", "BEScraper", "GEScraper", "JEPScraper"):
        monkeypatch.setattr(main, name, FailingSectionScraper)
    monkeypatch.setattr(main, "WeatherScraper", FailingWeatherScraper)
    monkeypatch.setattr(main, "FamilyNoticesScraper", FailingFamilyNoticesScraper)
    # Avoid picking up any real cached data for these email types.
    monkeypatch.setattr(main.email_cache, "load", lambda *args, **kwargs: None)
    return TestClient(main.app)


@pytest.mark.parametrize(
    "email_type",
    ["be", "ge", "jep", "aimpremium", "insider_jsy", "insider_gsy"],
)
def test_fetch_email_returns_partial_data_on_scraper_failure(client, email_type):
    response = client.get(f"/api/emails/{email_type}")

    assert response.status_code == 200, response.text

    data = response.json()
    assert isinstance(data, dict) and data

    # The failure is still reported to the user.
    warnings_header = response.headers.get("X-Email-Warnings")
    assert warnings_header is not None
    warnings = json.loads(warnings_header)
    assert warnings
    assert any("429" in w for w in warnings)


def test_fetch_email_returns_empty_story_lists(client):
    data = client.get("/api/emails/be").json()
    for field in [
        "news_stories",
        "sports_stories",
        "business_stories",
        "opinion_stories",
        "community_stories",
        "podcast_stories",
        "family_notices",
    ]:
        assert data[field] == []


@pytest.mark.parametrize(
    "email_type",
    ["be", "ge", "jep", "aimpremium", "insider_jsy", "insider_gsy"],
)
def test_render_empty_email_succeeds(client, email_type):
    response = client.get(f"/api/emails/{email_type}")
    assert response.status_code == 200

    render_response = client.post(f"/api/emails/{email_type}/render", json=response.json())
    assert render_response.status_code == 200, render_response.text
    assert "<html" in render_response.text.lower()

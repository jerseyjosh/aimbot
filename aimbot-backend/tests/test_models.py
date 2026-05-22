"""Tests for Pydantic models used throughout the aimbot backend."""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from aimbot.models.news import NewsStory, Advert, FamilyNotice, TopImage
from aimbot.models.emails import (
    BEEmailData,
    GEEmailData,
    JEPEmailData,
    ConnectInsiderEmailData,
    AIMPremiumEmailData,
    Foreword,
)
from aimbot.models.radio import RadioNewsData


# ---------------------------------------------------------------------------
# News model tests
# ---------------------------------------------------------------------------

class TestNewsStory:
    """Verify the NewsStory model."""

    def test_minimal_construction(self) -> None:
        """A NewsStory can be built with just headline, text, author, url."""
        story = NewsStory(
            headline="Test Headline",
            text="Some article text.",
            author="Test Author",
            url="https://example.com/story",
        )
        assert story.headline == "Test Headline"
        assert story.text == "Some article text."
        assert story.author == "Test Author"
        assert story.url == "https://example.com/story"
        # Defaults
        assert story.image_url == ""
        assert story.date is None

    def test_full_construction(self) -> None:
        """A NewsStory can be built with all fields."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        story = NewsStory(
            headline="Full Story",
            text="Full text.",
            date=dt,
            author="Author",
            url="https://example.com",
            image_url="https://example.com/img.png",
        )
        assert story.date == dt
        assert story.image_url == "https://example.com/img.png"

    def test_json_serializable(self) -> None:
        """NewsStory can be serialised to JSON and back."""
        dt = datetime(2025, 6, 1, 12, 0, 0)
        story = NewsStory(
            headline="JSON",
            text="Text.",
            date=dt,
            author="Author",
            url="https://example.com",
            image_url="https://example.com/img.png",
        )
        raw = story.model_dump_json()
        restored = NewsStory.model_validate_json(raw)
        assert restored.headline == "JSON"
        assert restored.date == dt

    def test_missing_required_fields(self) -> None:
        """ValidationError when headline, text, author, or url are missing."""
        with pytest.raises(ValidationError):
            NewsStory()  # type: ignore[call-arg]

    def test_repr(self) -> None:
        """__repr__ shows truncated headline and author."""
        story = NewsStory(
            headline="A" * 60,
            text="Text",
            author="Tester",
            url="https://example.com",
        )
        r = repr(story)
        assert r.startswith("NewsStory(headline='")
        assert "Tester" in r


class TestAdvert:
    """Verify the Advert model."""

    def test_construction(self) -> None:
        adv = Advert(url="https://example.com", image_url="https://example.com/img.png")
        assert adv.url == "https://example.com"
        assert adv.image_url == "https://example.com/img.png"

    def test_empty_urls(self) -> None:
        """Advert supports empty strings for URL fields."""
        adv = Advert(url="", image_url="")
        assert adv.url == ""
        assert adv.image_url == ""


class TestFamilyNotice:
    """Verify the FamilyNotice model."""

    def test_minimal(self) -> None:
        fn = FamilyNotice(name="John Smith", url="https://example.com/notice")
        assert fn.name == "John Smith"
        assert fn.funeral_director == ""
        assert fn.additional_text == ""

    def test_full(self) -> None:
        fn = FamilyNotice(
            name="Jane Doe",
            url="https://example.com/notice",
            funeral_director="Pitcher & Le Quesne",
            additional_text="Beloved mother",
        )
        assert fn.funeral_director == "Pitcher & Le Quesne"
        assert fn.additional_text == "Beloved mother"


class TestTopImage:
    """Verify the TopImage model."""

    def test_defaults(self) -> None:
        img = TopImage()
        assert img.url == ""
        assert img.author == ""
        assert img.text == ""
        assert img.link is None
        assert img.takeover is False

    def test_full(self) -> None:
        img = TopImage(
            url="https://example.com/img.png",
            author="Photographer",
            text="Sunset view",
            link="https://example.com",
            takeover=True,
        )
        assert img.takeover is True
        assert img.link == "https://example.com"


# ---------------------------------------------------------------------------
# Email data model tests
# ---------------------------------------------------------------------------

def _make_story(headline: str = "Story") -> NewsStory:
    return NewsStory(headline=headline, text="Text.", author="A", url="https://x.com")


def _make_top_image() -> TopImage:
    return TopImage(url="https://example.com/img.png", author="Photo")


class TestBEEmailData:
    """Verify the BE (Bailiwick Express Jersey) email model."""

    @staticmethod
    def _minimal_dict() -> dict:
        """Return a minimal valid BE email data dict."""
        s = _make_story()
        return {
            "top_image": _make_top_image(),
            "tides": "Low at 10:00",
            "weather": "Sunny",
            "date": "1 June 2025",
            "news_stories": [s],
            "spon_con_stories": [],
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "opinion_stories": [],
            "sports_stories": [],
            "business_stories": [],
            "connect_image_url": "",
            "community_stories": [],
            "podcast_stories": [],
            "family_notices": [],
        }

    def test_minimal_construction(self) -> None:
        data = BEEmailData(**self._minimal_dict())
        assert data.date == "1 June 2025"
        assert len(data.news_stories) == 1

    def test_json_round_trip(self) -> None:
        data = BEEmailData(**self._minimal_dict())
        raw = data.model_dump_json()
        restored = BEEmailData.model_validate_json(raw)
        assert restored.date == data.date
        assert len(restored.news_stories) == 1

    def test_repr(self) -> None:
        data = BEEmailData(**self._minimal_dict())
        r = repr(data)
        assert "1 June 2025" in r
        assert "1 news stories" in r


class TestGEEmailData:
    """Verify the GE (Bailiwick Express Guernsey) email model."""

    @staticmethod
    def _minimal_dict() -> dict:
        s = _make_story()
        return {
            "top_image": _make_top_image(),
            "tides": "Low at 11:00",
            "weather": "Cloudy",
            "date": "2 June 2025",
            "news_stories": [s],
            "spon_con_stories": [],
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "opinion_stories": [],
            "sports_stories": [],
            "business_stories": [],
            "connect_image_url": "",
            "community_stories": [],
            "podcast_stories": [],
        }

    def test_minimal_construction(self) -> None:
        data = GEEmailData(**self._minimal_dict())
        assert data.date == "2 June 2025"

    def test_extra_fields_ignored(self) -> None:
        """GEEmailData ignores extra fields (Pydantic v2 default)."""
        d = self._minimal_dict()
        d["extra_field"] = "ignored"  # Should not cause an error
        data = GEEmailData(**d)
        assert data.date == "2 June 2025"


class TestJEPEmailData:
    """Verify the JEP (Jersey Evening Post) email model."""

    def test_minimal(self) -> None:
        data = JEPEmailData(
            date="3 June 2025",
            jep_cover_url="",
            news_stories=[_make_story()],
            publication_cover_url="",
        )
        assert data.date == "3 June 2025"
        assert data.max_banner is None
        assert data.leaderboard_adverts == []
        assert data.mpu_adverts == []

    def test_with_adverts(self) -> None:
        adv = Advert(url="https://ad.com", image_url="https://ad.com/img.png")
        data = JEPEmailData(
            date="3 June 2025",
            jep_cover_url="",
            news_stories=[_make_story()],
            publication_cover_url="",
            max_banner=adv,
            leaderboard_adverts=[adv],
            mpu_adverts=[adv],
        )
        assert data.max_banner is not None
        assert len(data.leaderboard_adverts) == 1
        assert len(data.mpu_adverts) == 1


class TestConnectInsiderEmailData:
    """Verify the Connect Insider email model."""

    def test_minimal(self) -> None:
        s = _make_story()
        data = ConnectInsiderEmailData(
            top_image=_make_top_image(),
            big_stories=[s],
            sponsored_stories=[s],
            movers_and_shakers=[s],
            connect_image_url="",
            ads=[],
        )
        assert len(data.big_stories) == 1
        assert data.ads == []

    def test_sponsored_stories_fallback(self) -> None:
        """If business_stories is empty, sponsored_stories should be empty too (not crash)."""
        s = _make_story()
        data = ConnectInsiderEmailData(
            top_image=_make_top_image(),
            big_stories=[s],
            sponsored_stories=[],
            movers_and_shakers=[s],
            connect_image_url="",
            ads=[],
        )
        assert data.sponsored_stories == []


class TestAIMPremiumEmailData:
    """Verify the AIM Premium email model."""

    def test_minimal(self) -> None:
        data = AIMPremiumEmailData(
            title="Premium Title",
            news_stories=[_make_story()],
            foreword=Foreword.default(),
        )
        assert data.title == "Premium Title"
        assert data.foreword.title == ""
        assert data.foreword.author == ""

    def test_with_foreword(self) -> None:
        fw = Foreword(title="Editor's Note", author="Editor", job_title="Editor", image_url="", text="Hello")
        data = AIMPremiumEmailData(
            title="Premium",
            news_stories=[_make_story()],
            foreword=fw,
        )
        assert data.foreword.title == "Editor's Note"
        assert data.foreword.text == "Hello"


# ---------------------------------------------------------------------------
# Foreword tests
# ---------------------------------------------------------------------------

class TestForeword:
    """Verify the Foreword helper."""

    def test_default_all_empty(self) -> None:
        fw = Foreword.default()
        assert fw.title == ""
        assert fw.author == ""
        assert fw.job_title == ""
        assert fw.image_url == ""
        assert fw.text == ""

    def test_default_is_independent(self) -> None:
        """Each call to default() returns a new instance."""
        fw1 = Foreword.default()
        fw2 = Foreword.default()
        assert fw1 is not fw2


# ---------------------------------------------------------------------------
# RadioNewsData tests
# ---------------------------------------------------------------------------

class TestRadioNewsData:
    """Verify the RadioNewsData model including the generated_script computed field."""

    def test_generated_script_with_stories(self) -> None:
        s1 = NewsStory(headline="First", text="First story details.", author="A", url="https://x.com/1")
        s2 = NewsStory(headline="Second", text="Second story details.", author="A", url="https://x.com/2")
        data = RadioNewsData(
            speaker_id="Christie Bailey",
            stories=[s1, s2],
            weather="Sunny with a chance of rain.",
        )
        script = data.generated_script
        assert "Christie Bailey" in script
        assert "First story details" in script
        assert "Second story details" in script
        assert "Sunny with a chance of rain" in script
        assert "Bailiwick Radio News" in script
        assert "Bailiwick Express dot com" in script
        assert script.startswith("Bailiwick Radio News")
        assert script.endswith("Bailiwick Radio News.")

    def test_generated_script_no_stories(self) -> None:
        """generated_script handles an empty stories list gracefully."""
        data = RadioNewsData(
            speaker_id="Jodie Yettram",
            stories=[],
            weather="Cloudy.",
        )
        script = data.generated_script
        assert "Jodie Yettram" in script
        assert "Cloudy" in script
        # No story lines are added
        assert "First" not in script

    def test_script_defaults_to_empty(self) -> None:
        """The script field defaults to empty string, not generated_script."""
        data = RadioNewsData(
            speaker_id="Fiona Potigny",
            stories=[],
            weather="Windy.",
        )
        # script defaults to '' — the application sets it to generated_script
        # explicitly after creation (see radio_news.py RadioNews.get_data)
        assert data.script == ""
        assert data.generated_script != ""

    def test_script_can_be_overridden(self) -> None:
        """Providing an explicit script overrides generated_script."""
        data = RadioNewsData(
            speaker_id="Fiona Potigny",
            stories=[],
            weather="Windy.",
            script="Custom script content.",
        )
        assert data.script == "Custom script content."
        assert data.script != data.generated_script

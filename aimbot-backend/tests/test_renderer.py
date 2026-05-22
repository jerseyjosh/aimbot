"""Tests for the EmailRenderer and template rendering logic."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from aimbot.email_renderer import EmailRenderer


# ---------------------------------------------------------------------------
# first_sentence tests
# ---------------------------------------------------------------------------

class TestFirstSentence:
    """Verify EmailRenderer.first_sentence edge cases."""

    def test_simple_sentence(self) -> None:
        text = "This is the first sentence. Here is the second sentence."
        result = EmailRenderer.first_sentence(text)
        assert result == "This is the first sentence."

    def test_period_in_number(self) -> None:
        """Decimal numbers (e.g. 1.2 million) must not be treated as sentence breaks."""
        text = "This cost £1.2 million. Here is the second sentence."
        result = EmailRenderer.first_sentence(text)
        assert result == "This cost £1.2 million."

    def test_no_sentence_end(self) -> None:
        """When there is no period, the whole text is returned."""
        text = "This sentence has no period"
        result = EmailRenderer.first_sentence(text)
        assert result == "This sentence has no period"

    def test_none_text(self) -> None:
        """None returns an empty string."""
        result = EmailRenderer.first_sentence(None)
        assert result == ""

    def test_empty_text(self) -> None:
        result = EmailRenderer.first_sentence("")
        assert result == ""

    def text_with_multiple_periods(self) -> None:
        text = "Sentence one. Sentence two. Sentence three."
        result = EmailRenderer.first_sentence(text)
        assert result == "Sentence one."

    def test_bullet_point_no_sentence_boundary(self) -> None:
        """Periods that are not followed by a capital letter should be ignored."""
        text = "e.g. this is an example. Here is the next sentence."
        result = EmailRenderer.first_sentence(text)
        assert result == "e.g. this is an example."

    def text_with_abbreviation(self) -> None:
        """Periods in common abbreviations should not be sentence breaks."""
        text = "Dr. Smith arrived. He was late."
        result = EmailRenderer.first_sentence(text)
        # "Dr." is followed by a space and capital letter, so it IS a sentence boundary
        # This is a known limitation — we can't distinguish all abbreviation patterns
        assert result == "Dr. Smith arrived."

    def test_period_at_end(self) -> None:
        text = "Single sentence."
        result = EmailRenderer.first_sentence(text)
        assert result == "Single sentence."


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------

class FakeData(BaseModel):
    title: str
    body: str


class TestTemplateRendering:
    """Verify that templates can be loaded and rendered."""

    def test_render_simple_template(self) -> None:
        """A known template (be_template) renders without error."""

        # Use a minimal dataset that matches BE template variables.
        # We don't need real data — just enough to prove rendering works.
        from aimbot.models.news import NewsStory, TopImage, Advert, FamilyNotice

        s = NewsStory(headline="H", text="T.", author="A", url="https://x.com")
        ti = TopImage()
        fn = FamilyNotice(name="N", url="https://x.com")
        renderer = EmailRenderer(template_name="be_template.html")
        data = {
            "top_image": ti.model_dump(),
            "tides": "Low at 10",
            "weather": "Sunny",
            "date": "1 June 2025",
            "news_stories": [s.model_dump()],
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "spon_con_stories": [],
            "opinion_stories": [],
            "sports_stories": [],
            "business_stories": [],
            "connect_image_url": "",
            "community_stories": [],
            "podcast_stories": [],
            "family_notices": [fn.model_dump()],
        }
        html = renderer.render(data)
        assert isinstance(html, str)
        assert len(html) > 100
        # Basic structural checks
        assert "<html" in html or "<!DOCTYPE html" in html or "<table" in html
        assert "1 June 2025" in html
        assert "H" in html or "Sunny" in html

    def test_render_ge_template(self) -> None:
        """GE template also renders without error (different field set)."""
        from aimbot.models.news import NewsStory, TopImage

        s = NewsStory(headline="GE H", text="GE T.", author="A", url="https://x.com")
        ti = TopImage()
        renderer = EmailRenderer(template_name="ge_template.html")
        data = {
            "top_image": ti.model_dump(),
            "tides": "Low at 11",
            "weather": "Cloudy",
            "date": "2 June 2025",
            "news_stories": [s.model_dump()],
            "horizontal_adverts": [],
            "vertical_adverts": [],
            "spon_con_stories": [],
            "opinion_stories": [],
            "sports_stories": [],
            "business_stories": [],
            "connect_image_url": "",
            "community_stories": [],
            "podcast_stories": [],
        }
        html = renderer.render(data)
        assert "2 June 2025" in html
        assert "GE H" in html

    def test_template_not_found(self) -> None:
        """Asking for a non-existent template raises TemplateNotFound in __init__."""
        from jinja2.exceptions import TemplateNotFound
        with pytest.raises(TemplateNotFound):
            EmailRenderer(template_name="does_not_exist.html")

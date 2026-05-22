"""Unit tests for FamilyNoticesScraper helper methods.

These tests do NOT make network requests — they only exercise pure logic
in the scraper class (name formatting, notice parsing from known HTML).
"""

from __future__ import annotations

from bs4 import BeautifulSoup
import pytest

from aimbot.scrapers.family_notices import FamilyNoticesScraper


# ---------------------------------------------------------------------------
# format_name tests
# ---------------------------------------------------------------------------

class TestFormatName:
    """Verify the name-formatting logic."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # "Last, First" → "First Last"
            ("Smith, John", "John Smith"),
            # With bracketed parts (preserved with original casing)
            ("Smith, John (née Jones)", "John Smith (née Jones)"),
            # Multiple bracketed parts — acronyms preserved
            ("Doe, Jane (MBE) (JP)", "Jane Doe (MBE) (JP)"),
            # No comma — already formatted
            ("John Smith", "John Smith"),
            # With bracketed and comma
            ("Brown, Charlie (Retired)", "Charlie Brown (Retired)"),
            # 'née' should remain lowercase
            ("Smith, John (née Jones)", "John Smith (née Jones)"),
            # Bracketed part before name
            ("(Retired) Smith, John", "John Smith (Retired)"),
            # Empty name
            ("", ""),
            # Name with only bracketed parts
            ("(Unknown)", "(Unknown)"),
        ],
    )
    def test_format_name(self, raw: str, expected: str) -> None:
        result = FamilyNoticesScraper.format_name(raw)
        assert result == expected


# ---------------------------------------------------------------------------
# parse_notices tests (synthetic HTML)
# ---------------------------------------------------------------------------

class TestParseNotices:
    """Verify that HTML with notice cards is parsed correctly."""

    HTML_CARD = """
    <div class="notice-card">
        <h3>Smith, John</h3>
        <a href="https://example.com/notice/1">View Notice</a>
        <p>In loving memory of John. Pitcher & Le Quesne Funeral Directors.</p>
    </div>
    """

    HTML_CARD_MAILLARDS = """
    <div class="notice-card">
        <h3>Doe, Jane</h3>
        <a href="https://example.com/notice/2">View Notice</a>
        <p>Deeply missed. Maillards Funeral Directors.</p>
    </div>
    """

    HTML_CARD_ALSO_MAILLARDS = """
    <div class="notice-card">
        <h3>Maillard, Pierre</h3>
        <a href="https://example.com/notice/3">View Notice</a>
        <p>With deepest sympathy. Maillards Funeral Directors.</p>
    </div>
    """

    HTML_CARD_DE_GRUCHY = """
    <div class="notice-card">
        <h3>Brown, Alice</h3>
        <a href="https://example.com/notice/4">View Notice</a>
        <p>Forever in our hearts. De Gruchy's Funeral Care.</p>
    </div>
    """

    HTML_CARD_ALSO_DE_GRUCHY = """
    <div class="notice-card">
        <h3>De Gruchy, Robert</h3>
        <a href="https://example.com/notice/5">View Notice</a>
        <p>With thanks. De Gruchy's Funeral Care.</p>
    </div>
    """

    HTML_NO_DIRECTOR = """
    <div class="notice-card">
        <h3>Williams, Sarah</h3>
        <a href="https://example.com/notice/6">View Notice</a>
        <p>Sadly missed by all.</p>
    </div>
    """

    def test_single_notice_pitcher(self) -> None:
        soup = BeautifulSoup(self.HTML_CARD, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1
        assert notices[0].name == "John Smith"
        assert notices[0].url == "https://example.com/notice/1"
        assert notices[0].funeral_director == "Pitcher & Le Quesne Funeral Directors"

    def test_single_notice_maillards(self) -> None:
        soup = BeautifulSoup(self.HTML_CARD_MAILLARDS, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1
        assert notices[0].name == "Jane Doe"
        assert notices[0].funeral_director == "Maillards Funeral Directors"

    def test_maillards_in_name_no_match(self) -> None:
        """If 'Maillards' appears in the name itself, don't set funeral_director."""
        soup = BeautifulSoup(self.HTML_CARD_ALSO_MAILLARDS, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1
        # The name contains 'maillard' (lowercase) → skip
        assert notices[0].name == "Pierre Maillard"
        # Should NOT assign Maillards because 'maillard' is in the name
        assert notices[0].funeral_director == ""

    def test_de_gruchy_funeral_director(self) -> None:
        soup = BeautifulSoup(self.HTML_CARD_DE_GRUCHY, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1
        assert notices[0].name == "Alice Brown"
        assert notices[0].funeral_director == "De Gruchy's Funeral Care"

    def test_de_gruchy_in_name_no_match(self) -> None:
        """If 'de gruchy' appears in the name itself, don't set funeral_director."""
        soup = BeautifulSoup(self.HTML_CARD_ALSO_DE_GRUCHY, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1
        assert notices[0].name == "Robert De Gruchy"
        # Should NOT assign De Gruchy because 'de gruchy' is in the name
        assert notices[0].funeral_director == ""

    def test_no_funeral_director(self) -> None:
        """If no known funeral director is mentioned, the field stays empty."""
        soup = BeautifulSoup(self.HTML_NO_DIRECTOR, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1
        assert notices[0].name == "Sarah Williams"
        assert notices[0].funeral_director == ""

    def test_duplicate_notices_skipped(self) -> None:
        """Notices with the same name are only included once."""
        html = self.HTML_CARD + self.HTML_CARD  # same card twice
        soup = BeautifulSoup(html, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 1

    def test_multiple_unique_notices(self) -> None:
        """Multiple different notices are all returned."""
        html = self.HTML_CARD + self.HTML_CARD_MAILLARDS + self.HTML_NO_DIRECTOR
        soup = BeautifulSoup(html, "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert len(notices) == 3

    def test_empty_html(self) -> None:
        """HTML with no notice cards returns an empty list."""
        soup = BeautifulSoup("<html><body><p>Nothing here</p></body></html>", "html.parser")
        notices = FamilyNoticesScraper().parse_notices(soup)
        assert notices == []

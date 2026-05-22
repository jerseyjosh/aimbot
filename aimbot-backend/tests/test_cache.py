"""Tests for the JSON-file based EmailCache."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime

import pytest

from aimbot.cache import EmailCache, merge_with_cache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cache_dir(tmp_path: Path) -> str:
    """Return a temporary directory for cache files."""
    return str(tmp_path / "email_cache")


@pytest.fixture
def cache(cache_dir: str) -> EmailCache:
    """Return an EmailCache instance backed by a temp directory."""
    return EmailCache(cache_dir=cache_dir)


# ---------------------------------------------------------------------------
# EmailCache tests
# ---------------------------------------------------------------------------

class TestEmailCache:
    """Exercise the file-based email cache."""

    def test_save_and_load(self, cache: EmailCache, cache_dir: str) -> None:
        """Round-trip: save data, load it back, verify contents."""
        data = {"date": "1 January 2025", "news_stories": []}
        assert cache.save("be", data) is True

        loaded = cache.load("be")
        assert loaded == data

        # File should exist on disk
        filepath = Path(cache_dir) / "be.json"
        assert filepath.exists()

    def test_load_missing(self, cache: EmailCache) -> None:
        """Loading a cache key that does not exist returns None."""
        assert cache.load("nonexistent") is None

    def test_load_corrupt_file(self, cache: EmailCache, cache_dir: str) -> None:
        """A corrupt JSON file returns None without crashing."""
        filepath = Path(cache_dir) / "be.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text("this is not valid json {{{")

        assert cache.load("be") is None

    def test_clear(self, cache: EmailCache, cache_dir: str) -> None:
        """Clearing a cached type removes the file from disk."""
        cache.save("ge", {"foo": "bar"})
        assert Path(cache_dir, "ge.json").exists()

        assert cache.clear("ge") is True
        assert not Path(cache_dir, "ge.json").exists()

    def test_clear_nonexistent(self, cache: EmailCache) -> None:
        """Clearing a type that was never cached returns True (no-op)."""
        assert cache.clear("phantom") is True

    def test_save_with_datetime(self, cache: EmailCache) -> None:
        """Datetime objects in data are serialised to ISO-format strings."""
        now = datetime(2025, 6, 1, 10, 30, 0)
        data = {"updated": now, "label": "test"}
        assert cache.save("be", data) is True

        loaded = cache.load("be")
        assert loaded is not None
        assert loaded["updated"] == "2025-06-01T10:30:00"
        assert loaded["label"] == "test"

    def test_save_non_serializable(self, cache: EmailCache) -> None:
        """A value that cannot be JSON-serialised causes save to return False."""

        class Unserializable:
            pass

        data = {"bad": Unserializable()}
        # Should not crash; returns False
        assert cache.save("jep", data) is False

    def test_cache_dir_is_created(self, tmp_path: Path) -> None:
        """The cache directory is created automatically on init."""
        nested = tmp_path / "a" / "b" / "c"
        assert not nested.exists()

        c = EmailCache(cache_dir=str(nested))
        assert nested.exists()

    def test_multiple_types_independent(self, cache: EmailCache) -> None:
        """Data for different email types are stored in separate files."""
        cache.save("be", {"type": "BE"})
        cache.save("ge", {"type": "GE"})

        assert cache.load("be") == {"type": "BE"}
        assert cache.load("ge") == {"type": "GE"}
        assert cache.load("jep") is None


# ---------------------------------------------------------------------------
# merge_with_cache tests
# ---------------------------------------------------------------------------

class TestMergeWithCache:
    """Verify that fresh scraped data and cached user edits are merged correctly."""

    def test_no_cache_returns_fresh(self) -> None:
        """When there is no cached data, the fresh data is returned as-is."""
        fresh = {"news_stories": [], "weather": "Sunny"}
        result = merge_with_cache("be", fresh, None)
        assert result == fresh

    def test_user_fields_overlaid(self) -> None:
        """User-editable fields from cache override fresh data."""
        fresh = {"news_stories": [{"headline": "A"}], "top_image": {}, "weather": "Rain"}
        cached = {"top_image": {"url": "cached.png"}, "weather": "ShouldNotOverwrite"}
        result = merge_with_cache("be", fresh, cached)

        # top_image is user-editable for BE → should come from cache
        assert result["top_image"] == {"url": "cached.png"}
        # weather is NOT user-editable → keep fresh
        assert result["weather"] == "Rain"
        # non-user fields from fresh should remain
        assert result["news_stories"] == [{"headline": "A"}]

    def test_unknown_email_type_no_overlay(self) -> None:
        """An email type not listed in USER_EDITABLE_FIELDS gets no overlay."""
        fresh = {"x": 1, "y": 2}
        cached = {"x": 99}
        result = merge_with_cache("nonexistent", fresh, cached)
        assert result["x"] == 1  # fresh wins, no user fields defined

    def test_fresh_wins_for_non_editable(self) -> None:
        """Fresh data wins for fields not in USER_EDITABLE_FIELDS, even if in cache."""
        fresh = {"news_stories": [{"headline": "B"}], "opinion_stories": [{"headline": "C"}]}
        cached = {
            "news_stories": [{"headline": "OLD"}],
            "opinion_stories": [{"headline": "OLD_OPINION"}],
        }
        result = merge_with_cache("be", fresh, cached)
        # Both news_stories and opinion_stories are NOT in the user-editable list for BE
        assert result["news_stories"] == [{"headline": "B"}]
        assert result["opinion_stories"] == [{"headline": "C"}]

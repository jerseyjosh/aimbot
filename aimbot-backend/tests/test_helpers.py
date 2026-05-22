"""Tests for internal helper functions in the aimbot backend."""

from __future__ import annotations

import asyncio
import pytest

from aimbot.main import _gather_scraper_tasks


# ---------------------------------------------------------------------------
# _gather_scraper_tasks tests
# ---------------------------------------------------------------------------

class TestGatherScraperTasks:
    """Verify the concurrent scraper runner."""

    @pytest.mark.asyncio
    async def test_all_succeed(self) -> None:
        """When every task succeeds, results are returned keyed by name."""

        async def ok(name: str) -> str:
            return f"result-{name}"

        results = await _gather_scraper_tasks({"a": ok("a"), "b": ok("b")})
        assert results == {"a": "result-a", "b": "result-b"}

    @pytest.mark.asyncio
    async def test_one_fails(self) -> None:
        """A single failing task sets its result to None without crashing others."""

        async def will_fail() -> str:
            raise RuntimeError("Boom!")

        async def will_succeed() -> str:
            return "success"

        results = await _gather_scraper_tasks({"fail": will_fail(), "ok": will_succeed()})
        assert results["fail"] is None
        assert results["ok"] == "success"

    @pytest.mark.asyncio
    async def test_all_fail(self) -> None:
        """When every task fails, all results are None — no exception propagates."""

        async def fail(msg: str) -> str:
            raise ValueError(msg)

        results = await _gather_scraper_tasks(
            {"a": fail("err_a"), "b": fail("err_b")}
        )
        assert results == {"a": None, "b": None}

    @pytest.mark.asyncio
    async def test_empty_dict(self) -> None:
        """An empty dict of tasks returns an empty dict."""
        results = await _gather_scraper_tasks({})
        assert results == {}

    @pytest.mark.asyncio
    async def test_mixed_types(self) -> None:
        """Tasks that return different types are handled correctly."""

        async def returns_str() -> str:
            return "hello"

        async def returns_list() -> list:
            return [1, 2, 3]

        async def returns_none() -> None:
            return None

        results = await _gather_scraper_tasks(
            {"s": returns_str(), "l": returns_list(), "n": returns_none()}
        )
        assert results["s"] == "hello"
        assert results["l"] == [1, 2, 3]
        assert results["n"] is None  # None is a valid non-exception result

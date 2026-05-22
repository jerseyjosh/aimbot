"""Integration tests for the FastAPI application endpoints.

These tests use FastAPI's TestClient to send real HTTP requests through
the application stack without actually starting a server.  They verify
that routes are wired, error responses have the correct shape, and that
the global exception handler catches unexpected errors.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from aimbot.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    """Return a TestClient bound to the aimbot app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# API error shape tests
# ---------------------------------------------------------------------------

class TestAPIErrorShape:
    """Verify that API errors always return structured JSON with a 'detail' key."""

    def test_unknown_email_type_returns_json(self, client: TestClient) -> None:
        """GET /api/emails/unknown_type returns 422 (validation) or 400 with JSON."""
        resp = client.get("/api/emails/unknown_email_type")
        # Because EmailType is an Enum, FastAPI validation will catch invalid values
        # and return a 422 with a structured error body.
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body
        # The detail should be a list of validation errors
        assert isinstance(body["detail"], list)

    def test_missing_email_type_returns_json_error(self, client: TestClient) -> None:
        """GET /api/emails/invalidtype — invalid Enum value returns 422 JSON."""
        resp = client.get("/api/emails/invalidtype")
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_render_with_invalid_data_returns_json(self, client: TestClient) -> None:
        """POST /api/emails/be/render with invalid data returns validation error."""
        resp = client.post(
            "/api/emails/be/render",
            json={"bad_field": "garbage"},
        )
        # Pydantic validation should fail → 422
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_save_with_invalid_data_returns_json(self, client: TestClient) -> None:
        """POST /api/emails/be/save with invalid data returns validation error."""
        resp = client.post(
            "/api/emails/be/save",
            json={"not_a_valid_email": True},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_unknown_email_type_render_returns_json(self, client: TestClient) -> None:
        """POST /api/emails/xyzzy/render with valid data but bad type returns 422."""
        resp = client.post(
            "/api/emails/xyzzy/render",
            json={"some": "data"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body


# ---------------------------------------------------------------------------
# Global exception handler tests
# ---------------------------------------------------------------------------

class TestGlobalExceptionHandler:
    """Verify that unhandled exceptions return structured JSON, not HTML."""

    def test_unhandled_exception_returns_json(self) -> None:
        """Simulate an unhandled error inside an endpoint → expect JSON 500.

        Use raise_server_exceptions=False because ServerErrorMiddleware
        always re-raises the exception internally; TestClient with the
        default True would raise before we can inspect the response.
        """
        with patch("aimbot.main._gather_scraper_tasks") as mock:
            mock.side_effect = RuntimeError("Something went terribly wrong")

            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/api/emails/be")

        assert resp.status_code == 500
        body = resp.json()
        assert "detail" in body
        assert "Something went terribly wrong" in body["detail"]

    def test_exception_in_save_endpoint(self, client: TestClient) -> None:
        """Simulate an error in the save endpoint."""

        # We need valid BE data that passes Pydantic validation first
        valid_be_data = {
            "top_image": {"url": "", "author": "", "text": "", "takeover": False},
            "tides": "",
            "weather": "",
            "date": "1 June 2025",
            "news_stories": [],
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

        with patch("aimbot.main.email_cache.save") as mock:
            # Simulate a completely unexpected error (not even a proper exception)
            mock.side_effect = ValueError("Disk full")

            resp = client.post("/api/emails/be/save", json=valid_be_data)

        assert resp.status_code == 500
        body = resp.json()
        assert "detail" in body
        assert "Disk full" in body["detail"]


# ---------------------------------------------------------------------------
# Endpoint happy-path smoke tests
# ---------------------------------------------------------------------------

class TestEmailEndpointsSmoke:
    """Lightweight smoke tests for endpoint wiring.

    These test that endpoints are reachable and return the expected
    content-type structure.  Full integration tests with real scraped
    data belong in the dedicated scraper test files.
    """

    def test_get_be_email_fails_gracefully(self, client: TestClient) -> None:
        """GET /api/emails/be should attempt scraping and return JSON on failure."""
        resp = client.get("/api/emails/be")
        # Either it succeeds (200) with actual data, or fails with JSON (500)
        # Either way the response body should be parseable JSON.
        try:
            body = resp.json()
        except Exception:
            pytest.fail(f"Response body is not valid JSON: {resp.text[:200]}")

        if resp.status_code == 200:
            # It should have the shape of BEEmailData
            assert "news_stories" in body
            assert "date" in body
        else:
            # Error responses must have a 'detail' key
            assert "detail" in body, f"Error body missing 'detail': {body}"

    def test_get_ge_email_fails_gracefully(self, client: TestClient) -> None:
        """GET /api/emails/ge should attempt scraping and return JSON on failure."""
        resp = client.get("/api/emails/ge")
        try:
            body = resp.json()
        except Exception:
            pytest.fail(f"Response body is not valid JSON: {resp.text[:200]}")

        if resp.status_code == 200:
            assert "news_stories" in body
            assert "date" in body
        else:
            assert "detail" in body

    def test_get_jep_email_fails_gracefully(self, client: TestClient) -> None:
        """GET /api/emails/jep should attempt scraping and return JSON on failure."""
        resp = client.get("/api/emails/jep")
        try:
            body = resp.json()
        except Exception:
            pytest.fail(f"Response body is not valid JSON: {resp.text[:200]}")

        if resp.status_code == 200:
            assert "news_stories" in body
            assert "date" in body
        else:
            assert "detail" in body

    def test_get_aimpremium_email_fails_gracefully(self, client: TestClient) -> None:
        """GET /api/emails/aimpremium should attempt scraping and return JSON on failure."""
        resp = client.get("/api/emails/aimpremium")
        try:
            body = resp.json()
        except Exception:
            pytest.fail(f"Response body is not valid JSON: {resp.text[:200]}")

        if resp.status_code == 200:
            assert "news_stories" in body
            assert "title" in body
        else:
            assert "detail" in body

    def test_get_insider_jsy_email(self, client: TestClient) -> None:
        """GET /api/emails/insider_jsy should attempt scraping and return JSON on failure."""
        resp = client.get("/api/emails/insider_jsy")
        try:
            body = resp.json()
        except Exception:
            pytest.fail(f"Response body is not valid JSON: {resp.text[:200]}")

        if resp.status_code == 200:
            assert "big_stories" in body
        else:
            assert "detail" in body

    def test_get_insider_gsy_email(self, client: TestClient) -> None:
        """GET /api/emails/insider_gsy should attempt scraping and return JSON on failure."""
        resp = client.get("/api/emails/insider_gsy")
        try:
            body = resp.json()
        except Exception:
            pytest.fail(f"Response body is not valid JSON: {resp.text[:200]}")

        if resp.status_code == 200:
            assert "big_stories" in body
        else:
            assert "detail" in body

    def test_post_news_story_invalid_url(self, client: TestClient) -> None:
        """POST /api/news_stories/ with an unsupported URL should return 400 and JSON."""
        resp = client.post("/api/news_stories/?url=https://example.com")
        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body
        assert "Unknown" in body["detail"]

    def test_post_news_story_jep_returns_501(self, client: TestClient) -> None:
        """POST /api/news_stories/ with a JEP URL should return 501."""
        resp = client.post(
            "/api/news_stories/?url=https://jerseyeveningpost.com/some-story"
        )
        assert resp.status_code == 501
        body = resp.json()
        assert "detail" in body
        assert "not yet implemented" in body["detail"].lower()


# ---------------------------------------------------------------------------
# Radio endpoint tests
# ---------------------------------------------------------------------------

class TestRadioEndpoints:
    """Smoke tests for the radio endpoints."""

    def test_radio_speakers_returns_list(self, client: TestClient) -> None:
        """GET /api/radio/speakers returns a JSON list (potentially empty)."""
        resp = client.get("/api/radio/speakers")
        assert resp.status_code == 200
        speakers = resp.json()
        assert isinstance(speakers, list)

    def test_radio_generate_without_speaker(self, client: TestClient) -> None:
        """POST /api/radio/generate with an unknown speaker returns 400."""
        data = {
            "speaker_id": "Nonexistent Speaker",
            "script": "Test script.",
            "stories": [],
            "weather": "",
        }
        resp = client.post("/api/radio/generate", json=data)
        assert resp.status_code == 400
        body = resp.json()
        assert "detail" in body
        assert "not found" in body["detail"].lower()

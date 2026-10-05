import pytest

from aimbot.scrapers import config

PROXY_URL = "http://raspberrypi.example-tailnet.ts.net:8888"


def test_get_proxy_url_prefers_scraper_proxy(monkeypatch):
    monkeypatch.setenv("SCRAPER_PROXY_URL", PROXY_URL)
    monkeypatch.setenv("HTTPS_PROXY", "http://other-proxy:3128")
    assert config.get_proxy_url() == PROXY_URL


def test_get_proxy_url_falls_back_to_standard_env(monkeypatch):
    monkeypatch.delenv("SCRAPER_PROXY_URL", raising=False)
    monkeypatch.setenv("HTTPS_PROXY", PROXY_URL)
    assert config.get_proxy_url() == PROXY_URL


def test_get_proxy_url_returns_none_when_unset(monkeypatch):
    for env_var in config.PROXY_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    assert config.get_proxy_url() is None


@pytest.mark.asyncio
async def test_create_client_session_uses_configured_proxy(monkeypatch):
    monkeypatch.setenv("SCRAPER_PROXY_URL", PROXY_URL)
    async with config.create_client_session() as session:
        assert session._default_proxy == PROXY_URL


@pytest.mark.asyncio
async def test_create_client_session_forwards_kwargs(monkeypatch):
    monkeypatch.setenv("SCRAPER_PROXY_URL", PROXY_URL)
    async with config.create_client_session(headers={"X-Test": "1"}) as session:
        assert session._default_proxy == PROXY_URL
        assert session.headers["X-Test"] == "1"


@pytest.mark.asyncio
async def test_create_client_session_explicit_proxy_wins(monkeypatch):
    monkeypatch.setenv("SCRAPER_PROXY_URL", PROXY_URL)
    async with config.create_client_session(proxy="http://explicit:9999") as session:
        assert session._default_proxy == "http://explicit:9999"


@pytest.mark.asyncio
async def test_create_client_session_without_proxy(monkeypatch):
    for env_var in config.PROXY_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)
    async with config.create_client_session() as session:
        assert session._default_proxy is None

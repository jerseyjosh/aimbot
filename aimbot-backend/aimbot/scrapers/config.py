"""Shared configuration for the scraping layer.

Scraping traffic can be routed through an HTTP proxy (for example a tinyproxy
instance running on a Raspberry Pi and reachable over a Tailscale endpoint) by
setting the ``SCRAPER_PROXY_URL`` environment variable::

    SCRAPER_PROXY_URL=http://raspberrypi.your-tailnet.ts.net:8888

The standard ``HTTPS_PROXY``/``HTTP_PROXY`` variables are checked as a
fallback, so the process can also be pointed at a proxy purely through the
environment. ``NO_PROXY`` is intentionally not consulted here: an explicitly
configured proxy is considered authoritative for scraping traffic.
"""

import logging
import os
from typing import Optional

try:  # python-dotenv ships with uvicorn[standard]
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())
except ImportError:  # pragma: no cover - optional dependency
    pass

import aiohttp

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "josh@hakuna.co.uk"
}

# Checked in order; the first variable that is set wins.
PROXY_ENV_VARS = (
    "SCRAPER_PROXY_URL",
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
)


def get_proxy_url() -> Optional[str]:
    """Return the proxy URL that scraping requests should be routed through.

    Returns ``None`` when no proxy has been configured, in which case requests
    are made directly.
    """
    for env_var in PROXY_ENV_VARS:
        value = os.getenv(env_var)
        if value and value.strip():
            logger.debug("Routing scraping requests through proxy from %s", env_var)
            return value.strip()
    return None


def create_client_session(**kwargs) -> aiohttp.ClientSession:
    """Create an ``aiohttp.ClientSession`` routed through the scraping proxy.

    All extra keyword arguments (``headers``, ``timeout``, ``cookie_jar``, ...)
    are forwarded to ``aiohttp.ClientSession``. An explicitly supplied ``proxy``
    always takes precedence over the configured one.
    """
    proxy = get_proxy_url()
    if proxy is not None:
        kwargs.setdefault("proxy", proxy)
        logger.debug("Created scraping session using proxy %s", proxy)
    return aiohttp.ClientSession(**kwargs)

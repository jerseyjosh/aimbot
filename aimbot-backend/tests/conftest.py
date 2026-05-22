"""Shared fixtures and configuration for the aimbot test suite."""

from __future__ import annotations

from pathlib import Path
import pytest


# Tell pytest-asyncio to use "auto" mode so every async test works out of the box.
pytest_plugins = ("pytest_asyncio",)

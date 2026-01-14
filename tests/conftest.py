"""Pytest configuration and fixtures."""

import os
from pathlib import Path
from typing import Callable

import pytest

from bibtools.models import PaperMetadata
from bibtools.rate_limiter import reset_all_rate_limiters


@pytest.fixture
def make_metadata() -> Callable[..., PaperMetadata]:
    """Fixture factory to create PaperMetadata for testing."""

    def _make_metadata(
        title: str = "",
        authors: list[str] | None = None,
        venue: str | None = None,
        year: int | None = None,
        source: str = "crossref",
        doi: str | None = None,
        arxiv_id: str | None = None,
    ) -> PaperMetadata:
        # Convert simple author list to dict format
        author_dicts = []
        for author in authors or []:
            parts = author.split()
            if len(parts) >= 2:
                author_dicts.append({"given": " ".join(parts[:-1]), "family": parts[-1]})
            else:
                author_dicts.append({"given": "", "family": author})
        return PaperMetadata(
            title=title,
            authors=author_dicts,
            venue=venue,
            year=year,
            source=source,
            doi=doi,
            arxiv_id=arxiv_id,
        )

    return _make_metadata


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset rate limiters before each test for isolation."""
    reset_all_rate_limiters()
    yield


@pytest.fixture(autouse=True)
def load_env():
    """Load environment variables from .env file for tests."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
    yield

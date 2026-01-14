"""Metadata fetcher with single source of truth principle.

This module provides unified access to paper metadata from multiple sources:
- CrossRef: for papers with DOI
- DBLP: for conference papers without DOI (e.g., ICLR, some NeurIPS)
- arXiv: for arXiv preprints
"""

import os
import re
import time
from dataclasses import dataclass

import arxiv
import httpx

from . import logging as logger
from .models import Author, PaperMetadata
from .rate_limiter import get_rate_limiter
from .semantic_scholar import ResolvedIds, SemanticScholarClient
from .venue_aliases import get_canonical_venue

# =============================================================================
# Exceptions
# =============================================================================


class FetchError(Exception):
    """Base error for all metadata fetching errors."""

    pass


# =============================================================================
# arXiv Client
# =============================================================================


@dataclass
class ArxivMetadata:
    """Paper metadata from arXiv."""

    title: str
    authors: list[Author]
    year: int
    arxiv_id: str
    venue: str = "arXiv"


class ArxivClient:
    """Client for arXiv API."""

    def __init__(self) -> None:
        self._client = arxiv.Client()

    def get_paper_metadata(self, arxiv_id: str) -> ArxivMetadata | None:
        """Get paper metadata by arXiv ID."""
        normalized_id = self._normalize_arxiv_id(arxiv_id)
        try:
            search = arxiv.Search(id_list=[normalized_id])
            results = list(self._client.results(search))
            if not results:
                return None

            paper = results[0]
            authors = [self._parse_author_name(a.name) for a in paper.authors]
            authors = [a for a in authors if a]

            return ArxivMetadata(
                title=paper.title,
                authors=authors,
                year=paper.published.year,
                arxiv_id=normalized_id,
            )
        except arxiv.HTTPError as e:
            raise ArxivError(f"HTTP error fetching {arxiv_id}: {e}") from e
        except arxiv.UnexpectedEmptyPageError:
            return None
        except Exception as e:
            raise ArxivError(f"Error fetching {arxiv_id}: {e}") from e

    def _normalize_arxiv_id(self, arxiv_id: str) -> str:
        """Normalize arXiv ID: remove prefix and version suffix."""
        arxiv_id = arxiv_id.upper().removeprefix("ARXIV:").lower()
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.rsplit("v", 1)[0]
        return arxiv_id

    def _parse_author_name(self, name: str) -> Author | None:
        """Parse 'Firstname Lastname' into Author dict."""
        name = " ".join(name.split())
        if not name:
            return None
        # Filter out invalid author names (single words that are not names)
        # e.g., "NVIDIA", ":", organization names used as author placeholders
        if len(name) <= 2 or not any(c.isalpha() for c in name):
            return None
        # Skip if it looks like an organization (all caps, no spaces)
        if " " not in name and name.isupper():
            return None
        parts = name.rsplit(None, 1)
        if len(parts) == 2:
            return Author(given=parts[0], family=parts[1])
        return Author(given="", family=parts[0]) if parts else None


class ArxivError(FetchError):
    """Error from arXiv API."""

    pass


# =============================================================================
# CrossRef Client
# =============================================================================


@dataclass
class CrossRefMetadata:
    """Paper metadata from CrossRef."""

    title: str
    authors: list[Author]
    venue: str | None
    year: int | None
    doi: str


class CrossRefClient:
    """Client for CrossRef API."""

    BASE_URL = "https://api.crossref.org"
    _RATE_LIMIT = 0.02  # 50 req/sec for polite users

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._rate_limiter = get_rate_limiter("crossref", self._RATE_LIMIT)
        self._http_client: httpx.Client | None = None

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(
                timeout=30.0,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "bibtools/1.0 (https://github.com/bibtools; mailto:bibtools@example.com)",
                },
            )
        return self._http_client

    def close(self) -> None:
        if self._http_client is not None and not self._http_client.is_closed:
            self._http_client.close()
            self._http_client = None

    def get_paper_metadata(self, doi: str) -> CrossRefMetadata | None:
        """Get paper metadata by DOI."""
        doi = doi[4:] if doi.upper().startswith("DOI:") else doi
        message = self._fetch_work(doi)
        return self._parse_metadata(message, doi) if message else None

    def _fetch_work(self, doi: str) -> dict | None:
        client = self._get_http_client()
        request_url = f"{self.BASE_URL}/works/{doi}"

        for attempt in range(self.max_retries):
            try:
                response = self._rate_limiter.execute(lambda url=request_url: client.get(url))
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    time.sleep((attempt + 1) * 5)
                    continue
                response.raise_for_status()
                return response.json().get("message", {})
            except httpx.HTTPError as e:
                if attempt < self.max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise CrossRefError(f"Failed to fetch DOI {doi}: {e}") from e

        raise CrossRefError(f"Failed to fetch DOI {doi} after {self.max_retries} retries")

    def _parse_metadata(self, message: dict, doi: str) -> CrossRefMetadata:
        titles = message.get("title", [])
        title = titles[0] if titles else ""

        authors: list[Author] = []
        for author in message.get("author", []):
            if "family" in author:
                authors.append(Author(given=author.get("given", ""), family=author["family"]))

        containers = message.get("container-title", [])
        venue = containers[0] if containers else None

        year = None
        for date_field in ["published", "issued"]:
            date_parts = message.get(date_field, {}).get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
                break

        return CrossRefMetadata(title=title, authors=authors, venue=venue, year=year, doi=doi)


class CrossRefError(FetchError):
    """Error from CrossRef API."""

    pass


# =============================================================================
# DBLP Client
# =============================================================================


@dataclass
class DBLPMetadata:
    """Paper metadata from DBLP."""

    title: str
    authors: list[Author]
    year: int
    venue: str
    dblp_key: str
    doi: str | None = None


class DBLPClient:
    """Client for DBLP API."""

    BASE_URL = "https://dblp.org"

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def search_by_title(self, title: str, venue: str | None = None) -> DBLPMetadata | None:
        """Search for a paper by title (and optionally venue)."""
        if not title:
            return None

        try:
            query = title
            if venue:
                canonical = get_canonical_venue(venue)
                search_venue = canonical if canonical else venue
                if search_venue.upper() == "NEURIPS":
                    search_venue = "NIPS"
                query = f"{title} {search_venue}"

            logger.debug(f"DBLP title search: {query[:80]}...")

            resp = self._client.get(
                f"{self.BASE_URL}/search/publ/api",
                params={"q": query, "format": "json", "h": 10},
            )
            resp.raise_for_status()
            data = resp.json()

            hits = data.get("result", {}).get("hits", {}).get("hit", [])
            if not hits:
                return None

            for hit in hits:
                info = hit.get("info", {})
                hit_key = info.get("key", "")
                if hit_key.startswith("journals/corr"):
                    continue
                hit_title = (info.get("title") or "").rstrip(".")
                if self._titles_match(title, hit_title):
                    return self._parse_info(info, hit_key)

            return None

        except httpx.HTTPError as e:
            raise DBLPError(f"Failed to search DBLP for title: {title[:50]}") from e

    def _titles_match(self, title1: str, title2: str) -> bool:
        def normalize(t: str) -> str:
            t = re.sub(r"[^\w\s]", " ", t.lower())
            return " ".join(t.split())

        return normalize(title1) == normalize(title2)

    def _parse_info(self, info: dict, dblp_key: str) -> DBLPMetadata | None:
        title = info.get("title", "")
        if not title:
            return None
        title = title.rstrip(".")

        year_str = info.get("year", "")
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            return None

        venue = info.get("venue", "")

        authors_data = info.get("authors", {}).get("author", [])
        if isinstance(authors_data, dict):
            authors_data = [authors_data]
        authors = [self._parse_author(a) for a in authors_data]
        authors = [a for a in authors if a]

        doi = info.get("doi")

        return DBLPMetadata(title=title, authors=authors, year=year, venue=venue, dblp_key=dblp_key, doi=doi)

    def _parse_author(self, author_data: dict | str) -> Author | None:
        if isinstance(author_data, str):
            name = author_data
        else:
            name = author_data.get("text", "")

        if not name:
            return None

        name = re.sub(r"\s+\d{4}$", "", name)
        parts = name.rsplit(None, 1)
        if len(parts) == 2:
            return Author(given=parts[0], family=parts[1])
        return Author(given="", family=parts[0]) if parts else None


class DBLPError(FetchError):
    """Error from DBLP API."""

    pass


# =============================================================================
# Metadata Fetcher (orchestrator)
# =============================================================================


class MetadataFetcher:
    """Fetches paper metadata from CrossRef/DBLP/arXiv via S2 resolution."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        s2_client: SemanticScholarClient | None = None,
        crossref_client: CrossRefClient | None = None,
        dblp_client: DBLPClient | None = None,
        arxiv_client: ArxivClient | None = None,
    ):
        effective_api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.s2_client = s2_client or SemanticScholarClient(api_key=effective_api_key)
        self.crossref_client = crossref_client or CrossRefClient()
        self.dblp_client = dblp_client or DBLPClient()
        self.arxiv_client = arxiv_client or ArxivClient()
        self._owns_s2 = s2_client is None
        self._owns_crossref = crossref_client is None
        self._owns_dblp = dblp_client is None

    def close(self) -> None:
        if self._owns_s2:
            self.s2_client.close()
        if self._owns_crossref:
            self.crossref_client.close()
        if self._owns_dblp:
            self.dblp_client.close()

    def __enter__(self) -> "MetadataFetcher":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def fetch(self, paper_id: str) -> PaperMetadata | None:
        """Fetch paper metadata by paper_id.

        Flow:
        1. S2 resolves paper_id → DOI/arXiv ID + venue
        2. Source selection (mutually exclusive):
           - if DOI exists        → CrossRef
           - elif venue != arXiv  → DBLP
           - elif venue == arXiv  → arXiv
        """
        resolved = self.s2_client.resolve_ids(paper_id)
        if not resolved:
            logger.debug(f"Paper not found in Semantic Scholar: {paper_id}")
            return None

        logger.info(f"Resolved: {paper_id} | DOI={resolved.doi} | arXiv={resolved.arxiv_id} | venue={resolved.venue}")
        return self._fetch_with_resolved(resolved)

    def resolve_batch(self, paper_ids: list[str]) -> dict[str, ResolvedIds | None]:
        """Resolve multiple paper IDs via S2 batch API.

        This is much faster than calling resolve_ids() individually
        since it uses a single API request for up to 500 papers.
        """
        return self.s2_client.resolve_ids_batch(paper_ids)

    def fetch_with_resolved(self, resolved: ResolvedIds) -> PaperMetadata | None:
        """Fetch metadata using pre-resolved IDs (public wrapper)."""
        return self._fetch_with_resolved(resolved)

    def _fetch_with_resolved(self, resolved: ResolvedIds) -> PaperMetadata | None:
        # Case 1: DOI exists -> CrossRef
        if resolved.doi:
            logger.info("Source: crossref (DOI exists)")
            meta = self.crossref_client.get_paper_metadata(resolved.doi)
            if meta:
                return PaperMetadata(
                    title=meta.title,
                    authors=meta.authors,
                    year=meta.year,
                    venue=meta.venue,
                    doi=meta.doi,
                    arxiv_id=resolved.arxiv_id,
                    source="crossref",
                )
            return None

        # Case 2: No DOI, venue != arXiv -> DBLP
        if not self._is_arxiv_venue(resolved.venue):
            logger.info(f"Source: dblp (venue={resolved.venue})")
            if resolved.title:
                meta = self.dblp_client.search_by_title(resolved.title, resolved.venue)
                if meta:
                    return PaperMetadata(
                        title=meta.title,
                        authors=meta.authors,
                        year=meta.year,
                        venue=meta.venue,
                        doi=meta.doi,
                        arxiv_id=resolved.arxiv_id,
                        source="dblp",
                    )
            return None

        # Case 3: No DOI, venue == arXiv -> arXiv
        if resolved.arxiv_id:
            logger.info("Source: arxiv")
            meta = self.arxiv_client.get_paper_metadata(resolved.arxiv_id)
            if meta:
                return PaperMetadata(
                    title=meta.title,
                    authors=meta.authors,
                    year=meta.year,
                    venue=meta.venue,
                    arxiv_id=meta.arxiv_id,
                    source="arxiv",
                )

        return None

    def _is_arxiv_venue(self, venue: str | None) -> bool:
        if not venue:
            return True
        venue_lower = venue.lower()
        return "arxiv" in venue_lower or venue_lower in ("", "corr")

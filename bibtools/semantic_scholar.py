"""Semantic Scholar API client for identifier resolution."""

import time
from dataclasses import dataclass

import httpx

from .rate_limiter import get_rate_limiter

_BATCH_SIZE = 500


@dataclass
class ResolvedIds:
    """Resolved external IDs from Semantic Scholar.

    These IDs are used to fetch metadata from the appropriate source of truth.
    Priority: DOI (CrossRef) > venue != arXiv (DBLP) > arXiv
    """

    paper_id: str
    doi: str | None
    arxiv_id: str | None
    dblp_id: str | None  # e.g., "conf/iclr/HuSWALWWC22"
    venue: str | None = None  # e.g., "ICLR", "NeurIPS", "arXiv"
    title: str | None = None  # Paper title for DBLP title-based search


class SemanticScholarClient:
    """Semantic Scholar API client for identifier resolution.

    Role: Resolve paper identifiers (arXiv ID, DOI, S2 ID) to external IDs
    for downstream metadata fetching from CrossRef/DBLP/arXiv.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    # Rate limits: with API key = 1 req/sec, without = 100 req/5min (~3 sec)
    _RATE_LIMIT_WITH_KEY = 1.0
    _RATE_LIMIT_NO_KEY = 3.0

    def __init__(self, api_key: str | None = None, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        interval = self._RATE_LIMIT_WITH_KEY if api_key else self._RATE_LIMIT_NO_KEY
        self._rate_limiter = get_rate_limiter("semantic_scholar", interval)
        self._http_client: httpx.Client | None = None

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client with connection pooling."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(
                timeout=30.0,
                headers=self._get_headers(),
                http2=True,
            )
        return self._http_client

    def close(self) -> None:
        """Close the HTTP client.

        Note: Prefer using context manager (with statement) for automatic cleanup:
            with SemanticScholarClient() as client:
                client.search_by_title("...")
        """
        if self._http_client is not None and not self._http_client.is_closed:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "SemanticScholarClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Make a request with retry logic for rate limiting.

        Args:
            method: HTTP method.
            url: URL to request.
            **kwargs: Additional arguments for httpx.

        Returns:
            Response object.
        """
        last_error = None
        client = self._get_http_client()

        for attempt in range(self.max_retries):
            try:
                # Use rate limiter to execute the request
                response = self._rate_limiter.execute(lambda: client.request(method, url, **kwargs))

                if response.status_code == 429:
                    # Rate limited - wait longer and retry
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    time.sleep(wait_time)
                    last_error = httpx.HTTPStatusError(
                        f"Rate limited (attempt {attempt + 1}/{self.max_retries})",
                        request=response.request,
                        response=response,
                    )
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep((attempt + 1) * 5)
                    continue
                raise

        if last_error:
            raise ConnectionError(f"Failed after {self.max_retries} retries: {last_error}") from last_error
        raise ConnectionError("Request failed with unknown error")

    def search_by_title(self, title: str, limit: int = 5) -> list[ResolvedIds]:
        """Search for papers by title.

        Args:
            title: Paper title to search for.
            limit: Maximum number of results.

        Returns:
            List of ResolvedIds with paper info.
        """
        clean_title = title.replace("{", "").replace("}", "").replace("$", "")

        params = {
            "query": clean_title,
            "limit": limit,
            "fields": "paperId,externalIds,venue,title",
        }

        try:
            response = self._request_with_retry(
                "GET",
                f"{self.BASE_URL}/paper/search",
                params=params,
            )
            data = response.json()
            papers = data.get("data", []) or []
            results = []
            for p in papers:
                resolved = self._parse_resolved_ids(p)
                if resolved:
                    results.append(resolved)
            return results
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to search Semantic Scholar: {e}") from e

    def resolve_ids(self, paper_id: str) -> ResolvedIds | None:
        """Resolve any paper identifier to DOI/arXiv ID.

        This is the primary entry point for the new architecture.
        Returns DOI and arXiv ID for downstream metadata fetching.

        Supports:
        - arXiv ID: "2106.09685" or "ARXIV:2106.09685"
        - DOI: "10.1234/..." or "DOI:10.1234/..."
        - Semantic Scholar ID: "649def34f8be52c8b66281af98ae884c09aef38b"
        """
        # Normalize arXiv ID (add ARXIV: prefix if looks like arXiv ID)
        normalized_id = self._normalize_paper_id(paper_id)

        try:
            response = self._request_with_retry(
                "GET",
                f"{self.BASE_URL}/paper/{normalized_id}",
                params={"fields": "paperId,externalIds,venue,title"},
            )
            return self._parse_resolved_ids(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError:
            return None

    def _normalize_paper_id(self, paper_id: str) -> str:
        """Normalize paper ID for Semantic Scholar API.

        Adds ARXIV: prefix to bare arXiv IDs (e.g., "2106.09685" -> "ARXIV:2106.09685").
        """
        # Already has a prefix
        if ":" in paper_id or "/" in paper_id:
            return paper_id

        # Check if it looks like an arXiv ID (YYMM.NNNNN format)
        import re

        if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", paper_id):
            return f"ARXIV:{paper_id}"

        return paper_id

    def resolve_ids_batch(self, paper_ids: list[str]) -> dict[str, ResolvedIds | None]:
        """Resolve multiple paper identifiers to DOI/arXiv ID in batch."""
        if not paper_ids:
            return {}

        results: dict[str, ResolvedIds | None] = {}
        for i in range(0, len(paper_ids), _BATCH_SIZE):
            batch = paper_ids[i : i + _BATCH_SIZE]
            batch_results = self._resolve_ids_batch_single(batch)
            results.update(batch_results)
        return results

    def _resolve_ids_batch_single(self, paper_ids: list[str]) -> dict[str, ResolvedIds | None]:
        """Resolve a single batch of paper identifiers."""
        if not paper_ids:
            return {}

        try:
            response = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/paper/batch",
                params={"fields": "paperId,externalIds,venue,title"},
                json={"ids": paper_ids},
            )
            data = response.json()

            results: dict[str, ResolvedIds | None] = {}
            for paper_id, paper_data in zip(paper_ids, data, strict=True):
                if paper_data is None:
                    results[paper_id] = None
                else:
                    results[paper_id] = self._parse_resolved_ids(paper_data)
            return results
        except httpx.HTTPError:
            return {pid: None for pid in paper_ids}

    def _parse_resolved_ids(self, data: dict) -> ResolvedIds | None:
        """Parse API response into ResolvedIds."""
        if not data:
            return None

        paper_id = data.get("paperId", "")
        if not paper_id:
            return None

        external_ids = data.get("externalIds", {}) or {}
        doi = external_ids.get("DOI")
        arxiv_id = external_ids.get("ArXiv")
        dblp_id = external_ids.get("DBLP")
        venue = data.get("venue") or None
        title = data.get("title") or None

        # Skip arXiv DOIs (e.g., 10.48550/arXiv.xxxx) - treat as arXiv-only
        if doi and "arxiv" in doi.lower():
            doi = None

        return ResolvedIds(
            paper_id=paper_id,
            doi=doi,
            arxiv_id=arxiv_id,
            dblp_id=dblp_id,
            venue=venue,
            title=title,
        )

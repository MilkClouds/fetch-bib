"""Tests for Semantic Scholar API client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from bibtools.semantic_scholar import SemanticScholarClient


class TestSemanticScholarClientInit:
    """Tests for client initialization."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = SemanticScholarClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client._rate_limiter.min_interval == 1.0  # With key

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        client = SemanticScholarClient()
        assert client.api_key is None
        assert client._rate_limiter.min_interval == 3.0  # Without key

    def test_get_headers_with_key(self):
        """Test headers include API key when provided."""
        client = SemanticScholarClient(api_key="test_key_headers")
        headers = client._get_headers()
        assert headers["x-api-key"] == "test_key_headers"
        assert headers["Accept"] == "application/json"

    def test_get_headers_without_key(self):
        """Test headers without API key."""
        client = SemanticScholarClient()
        headers = client._get_headers()
        assert "x-api-key" not in headers
        assert headers["Accept"] == "application/json"


class TestSearchByTitle:
    """Tests for search_by_title method."""

    @patch.object(SemanticScholarClient, "_request_with_retry")
    def test_search_success(self, mock_request):
        """Test successful search returns ResolvedIds."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "1", "externalIds": {"DOI": "10.1/a"}, "venue": "NeurIPS", "title": "Paper One"},
                {"paperId": "2", "externalIds": {"ArXiv": "2301.00001"}, "venue": "arXiv", "title": "Paper Two"},
            ]
        }
        mock_request.return_value = mock_response

        client = SemanticScholarClient(api_key="test_search_1")
        results = client.search_by_title("machine learning", limit=5)

        assert len(results) == 2
        assert results[0].paper_id == "1"
        assert results[0].doi == "10.1/a"
        assert results[0].title == "Paper One"
        assert results[1].paper_id == "2"
        assert results[1].arxiv_id == "2301.00001"

    @patch.object(SemanticScholarClient, "_request_with_retry")
    def test_search_empty_results(self, mock_request):
        """Test search with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_request.return_value = mock_response

        client = SemanticScholarClient(api_key="test_search_2")
        results = client.search_by_title("nonexistent paper xyz", limit=5)

        assert len(results) == 0

    @patch.object(SemanticScholarClient, "_request_with_retry")
    def test_search_cleans_latex(self, mock_request):
        """Test that search cleans LaTeX braces from title."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_request.return_value = mock_response

        client = SemanticScholarClient(api_key="test_search_3")
        client.search_by_title("{CNN} for {NLP}")

        call_args = mock_request.call_args
        params = call_args.kwargs.get("params", {})
        assert "{" not in params["query"]
        assert "}" not in params["query"]

    @patch.object(SemanticScholarClient, "_request_with_retry")
    def test_search_http_error(self, mock_request):
        """Test search with HTTP error."""
        mock_request.side_effect = httpx.HTTPError("Connection failed")

        client = SemanticScholarClient(api_key="test_search_4")
        with pytest.raises(ConnectionError, match="Failed to search"):
            client.search_by_title("test")

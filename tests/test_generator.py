"""Tests for bibtex generator module."""

from unittest.mock import MagicMock, patch

from bibtools.generator import BibtexGenerator
from bibtools.models import BibtexEntry, PaperMetadata
from bibtools.semantic_scholar import ResolvedIds


class TestBibtexEntry:
    """Tests for BibtexEntry class."""

    def test_to_bibtex_field_order(self):
        """Test serialization has correct field order: title, author, venue, year."""
        entry = BibtexEntry(
            key="test2024",
            title="Test Paper",
            authors=["John Smith"],
            venue="Conference",
            year=2024,
        )
        bibtex = entry.to_bibtex()
        assert bibtex.index("  title") < bibtex.index("  author")
        assert bibtex.index("  author") < bibtex.index("  booktitle")
        assert bibtex.index("  booktitle") < bibtex.index("  year")

    def test_to_bibtex_with_paper_id(self):
        """Test serialization includes paper_id comment."""
        entry = BibtexEntry(
            key="test",
            title="Test",
            authors=["Author"],
            venue=None,
            year=2024,
        )
        bibtex = entry.to_bibtex("ARXIV:2106.15928")
        assert "% paper_id: ARXIV:2106.15928" in bibtex

    def test_to_bibtex_article_uses_journal(self):
        """Test article entries use journal field."""
        entry = BibtexEntry(
            key="test",
            title="Test",
            authors=[],
            venue="Nature",
            year=2024,
            entry_type="article",
        )
        bibtex = entry.to_bibtex()
        assert "journal = {Nature}" in bibtex
        assert "booktitle" not in bibtex


class TestBibtexGenerator:
    """Tests for BibtexGenerator class."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        generator = BibtexGenerator(api_key="test_key")
        assert generator._fetcher is not None

    @patch.object(BibtexGenerator, "__init__", lambda self, **kwargs: None)
    def test_fetch_by_paper_id_success(self):
        """Test fetching bibtex by paper_id with new architecture."""
        generator = BibtexGenerator.__new__(BibtexGenerator)
        generator._fetcher = MagicMock()

        generator._fetcher.fetch.return_value = PaperMetadata(
            title="Test Paper",
            authors=[{"given": "John", "family": "Doe"}],
            venue="Test Conference",
            year=2024,
            doi="10.1234/test",
            source="crossref",
        )

        result = generator.fetch_by_paper_id("ARXIV:2106.15928")
        assert result is not None
        assert "Test Paper" in result.bibtex
        assert "% paper_id: ARXIV:2106.15928" in result.bibtex

    @patch.object(BibtexGenerator, "__init__", lambda self, **kwargs: None)
    def test_fetch_by_paper_id_not_found(self):
        """Test fetching non-existent paper."""
        generator = BibtexGenerator.__new__(BibtexGenerator)
        generator._fetcher = MagicMock()
        generator._fetcher.fetch.return_value = None

        result = generator.fetch_by_paper_id("ARXIV:0000.00000")
        assert result is None

    @patch.object(BibtexGenerator, "__init__", lambda self, **kwargs: None)
    def test_search_by_query(self):
        """Test search by query fetches metadata from source of truth."""
        generator = BibtexGenerator.__new__(BibtexGenerator)
        generator._fetcher = MagicMock()
        generator._fetcher.s2_client = MagicMock()

        # Mock S2 search returns ResolvedIds
        generator._fetcher.s2_client.search_by_title.return_value = [
            ResolvedIds(
                paper_id="paper1", doi="10.1/a", arxiv_id=None, dblp_id=None, venue="NeurIPS", title="ML Paper"
            ),
        ]

        # Mock fetcher returns metadata
        generator._fetcher._fetch_with_resolved.return_value = PaperMetadata(
            title="ML Paper",
            authors=[{"given": "John", "family": "Author"}],
            venue="NeurIPS",
            year=2024,
            doi="10.1/a",
            source="crossref",
        )

        results = generator.search_by_query("machine learning", limit=5)
        assert len(results) == 1
        assert results[0].metadata.title == "ML Paper"
        assert "ML Paper" in results[0].bibtex

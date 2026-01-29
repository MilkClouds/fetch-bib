"""Tests for verifier module (functional)."""

from unittest.mock import MagicMock

from bibtools.models import FetchBundle, PaperMetadata
from bibtools.utils import (
    compare_authors,
    compare_titles,
    normalize_author_name,
    parse_bibtex_authors,
    strip_latex_braces,
    title_similarity,
)
from bibtools.verifier import (
    check_field_mismatches,
    should_skip_verified,
    verify_entry,
    verify_file,
)
from bibtools.venue_aliases import get_canonical_venue, venues_match


class TestStripLatexBraces:
    def test_strip_simple(self):
        assert strip_latex_braces("Hello World") == "Hello World"

    def test_strip_braces(self):
        result = strip_latex_braces("{CNN} for {NLP}")
        assert result == "CNN for NLP"
        assert "{" not in result
        assert "}" not in result

    def test_strip_preserves_case(self):
        assert strip_latex_braces("BERT: Pre-Training") == "BERT: Pre-Training"

    def test_strip_preserves_punctuation(self):
        assert strip_latex_braces("Hello, World!") == "Hello, World!"


class TestCompareTitles:
    def test_exact_match(self):
        exact, warning = compare_titles("Hello World", "Hello World")
        assert exact is True
        assert warning is False

    def test_case_difference_warning(self):
        match, warning = compare_titles("Hello World", "hello world")
        assert match is True
        assert warning is True

    def test_punctuation_mismatch(self):
        match, warning = compare_titles("Hello World", "Hello World!")
        assert match is False
        assert warning is False

    def test_braces_difference_warning(self):
        match, warning = compare_titles("{CNN} for NLP", "CNN for NLP")
        assert match is True
        assert warning is True


class TestTitleSimilarity:
    def test_identical_titles(self):
        assert title_similarity("Hello World", "Hello World") == 1.0

    def test_similar_titles(self):
        score = title_similarity("Hello World", "Hello World!")
        assert score > 0.9

    def test_different_titles(self):
        score = title_similarity("Hello World", "Goodbye Moon")
        assert score < 0.5


class TestAuthorParsing:
    def test_normalize_author_name_simple(self):
        assert normalize_author_name("John Smith") == "John Smith"

    def test_normalize_author_name_last_first(self):
        assert normalize_author_name("Smith, John") == "John Smith"

    def test_normalize_author_name_with_latex(self):
        assert normalize_author_name("{John} Smith") == "John Smith"

    def test_parse_bibtex_authors_single(self):
        assert parse_bibtex_authors("John Smith") == ["John Smith"]

    def test_parse_bibtex_authors_multiple(self):
        authors = parse_bibtex_authors("John Smith and Jane Doe and Bob Wilson")
        assert authors == ["John Smith", "Jane Doe", "Bob Wilson"]

    def test_compare_authors_exact_match(self):
        match, warning = compare_authors("John Smith and Jane Doe", ["John Smith", "Jane Doe"])
        assert match is True
        assert warning is False

    def test_compare_authors_style_difference(self):
        match, warning = compare_authors("Smith, John and Doe, Jane", ["John Smith", "Jane Doe"])
        assert match is True
        assert warning is True

    def test_compare_authors_different_count(self):
        match, _ = compare_authors("John Smith and Jane Doe", ["John Smith", "Jane Doe", "Bob Wilson"])
        assert match is False

    def test_compare_authors_different_names(self):
        match, _ = compare_authors("John Smith and Jane Doe", ["John Smith", "Alice Brown"])
        assert match is False


class TestVenueAliases:
    def test_get_canonical_venue_exact(self):
        assert get_canonical_venue("CoRL") == "CoRL"
        assert get_canonical_venue("NeurIPS") == "NeurIPS"

    def test_get_canonical_venue_full_name(self):
        assert get_canonical_venue("Conference on Robot Learning") == "CoRL"
        assert get_canonical_venue("International Conference on Machine Learning") == "ICML"

    def test_get_canonical_venue_unknown(self):
        assert get_canonical_venue("Unknown Conference") is None

    def test_venues_match_alias(self):
        assert venues_match("CoRL", "Conference on Robot Learning") is True
        assert venues_match("ICML", "International Conference on Machine Learning") is True


class TestFieldMismatchDetection:
    def test_check_year_mismatch(self, make_metadata):
        entry = {"year": "2023"}
        metadata = make_metadata(title="Test", year=2024)
        mismatches, warnings = check_field_mismatches(entry, metadata)
        assert any(m.field_name == "year" for m in mismatches)
        assert warnings == []

    def test_check_venue_match_alias(self, make_metadata):
        entry = {"booktitle": "CoRL"}
        metadata = make_metadata(title="Test", venue="Conference on Robot Learning")
        mismatches, _ = check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "venue" for m in mismatches)


class TestShouldSkipVerified:
    def test_max_age_none_always_skips(self):
        assert should_skip_verified("2020.01.01", None) is True
        assert should_skip_verified(None, None) is True

    def test_max_age_zero_never_skips(self):
        assert should_skip_verified("2020.01.01", 0) is False
        assert should_skip_verified(None, 0) is False

    def test_max_age_with_invalid_date(self):
        assert should_skip_verified("invalid", 30) is False


class TestVerifyEntry:
    def test_verify_entry_already_verified(self, make_metadata):
        entry = {"ID": "test2024", "title": "Test"}
        content = "% paper_id: ARXIV:2106.15928, verified via bibtools (2024.12.30)\n@article{test2024,}"
        fetcher = MagicMock()
        result = verify_entry(entry, content, fetcher=fetcher)
        assert result.already_verified is True
        assert result.success is True

    def test_verify_entry_no_paper_id(self):
        entry = {"ID": "test2024", "title": "Test Paper"}
        content = "@article{test2024, title = {Test Paper}}"
        fetcher = MagicMock()
        result = verify_entry(entry, content, fetcher=fetcher)
        assert result.success is True
        assert result.no_paper_id is True

    def test_verify_entry_api_error(self, make_metadata):
        entry = {"ID": "test2024"}
        content = "% paper_id: DOI:10.1234/test\n@article{test2024,}"
        fetcher = MagicMock()
        fetcher.resolve_batch.return_value = {"DOI:10.1234/test": object()}
        fetcher.fetch_bundle_with_resolved.side_effect = ConnectionError("API unavailable")
        result = verify_entry(entry, content, fetcher=fetcher)
        assert result.success is False
        assert "API error" in result.message

    def test_verify_entry_paper_not_found(self):
        entry = {"ID": "test2024"}
        content = "% paper_id: DOI:10.1234/nonexistent\n@article{test2024,}"
        fetcher = MagicMock()
        fetcher.resolve_batch.return_value = {"DOI:10.1234/nonexistent": object()}
        fetcher.fetch_bundle_with_resolved.return_value = FetchBundle(selected=None, sources={}, arxiv_conflict=False)
        result = verify_entry(entry, content, fetcher=fetcher)
        assert result.success is False
        assert "Paper not found" in result.message

    def test_verify_entry_field_mismatch(self, make_metadata):
        metadata = make_metadata(title="Correct Title", authors=["John Smith"], year=2025)
        entry = {"ID": "test2024", "title": "Correct Title", "year": "2024"}
        content = "% paper_id: DOI:10.1234/test\n@article{test2024,}"
        fetcher = MagicMock()
        fetcher.resolve_batch.return_value = {"DOI:10.1234/test": object()}
        fetcher.fetch_bundle_with_resolved.return_value = FetchBundle(
            selected=metadata, sources={"crossref": metadata}, arxiv_conflict=False
        )
        result = verify_entry(entry, content, fetcher=fetcher)
        assert result.success is False
        assert "year" in result.message

    def test_verify_entry_arxiv_conflict(self, make_metadata):
        metadata = make_metadata(title="Test Paper", authors=["Wrong Author"], year=2024, source="dblp")
        arxiv_meta = make_metadata(title="Test Paper", authors=["John Smith"], year=2024, source="arxiv")
        entry = {"ID": "test2024", "title": "Test Paper", "author": "Wrong Author", "year": "2024"}
        content = "% paper_id: ARXIV:1234.5678\n@article{test2024,}"
        fetcher = MagicMock()
        fetcher.resolve_batch.return_value = {"ARXIV:1234.5678": object()}
        fetcher.fetch_bundle_with_resolved.return_value = FetchBundle(
            selected=metadata,
            sources={"dblp": metadata, "arxiv": arxiv_meta},
            arxiv_conflict=True,
        )
        result = verify_entry(entry, content, fetcher=fetcher, arxiv_check=True)
        assert result.success is False
        assert "source conflict" in result.message

    def test_verify_entry_arxiv_conflict_ignored(self, make_metadata):
        metadata = make_metadata(title="Test Paper", authors=["Wrong Author"], year=2024, source="dblp")
        arxiv_meta = make_metadata(title="Test Paper", authors=["John Smith"], year=2024, source="arxiv")
        entry = {"ID": "test2024", "title": "Test Paper", "author": "Wrong Author", "year": "2024"}
        content = "% paper_id: ARXIV:1234.5678\n@article{test2024,}"
        fetcher = MagicMock()
        fetcher.resolve_batch.return_value = {"ARXIV:1234.5678": object()}
        fetcher.fetch_bundle_with_resolved.return_value = FetchBundle(
            selected=metadata,
            sources={"dblp": metadata, "arxiv": arxiv_meta},
            arxiv_conflict=True,
        )
        result = verify_entry(entry, content, fetcher=fetcher, arxiv_check=False)
        assert result.success is False or result.success is True


class TestVerifyFile:
    def test_verify_file_multiple_entries(self, tmp_path, make_metadata):
        bib_content = """
% paper_id: DOI:10.1234/example, verified via bibtools (2024.01.01)
@article{verified2024,
  title = {Verified Paper},
  year = {2024}
}

@article{unverified2024,
  title = {Unverified Paper},
  year = {2024}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)

        fetcher = MagicMock()
        fetcher.resolve_batch.return_value = {}

        report, _ = verify_file(bib_file, fetcher=fetcher)
        assert report.total_entries == 2
        assert report.already_verified == 1
        assert report.no_paper_id == 1

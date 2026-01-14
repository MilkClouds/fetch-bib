"""Tests for verifier module."""

from unittest.mock import MagicMock

from bibtools.utils import (
    compare_authors,
    compare_titles,
    normalize_author_name,
    parse_bibtex_authors,
    strip_latex_braces,
    title_similarity,
)
from bibtools.venue_aliases import get_canonical_venue, venues_match
from bibtools.verifier import BibVerifier


class TestStripLatexBraces:
    """Tests for strip_latex_braces function."""

    def test_strip_simple(self):
        """Test stripping a simple title preserves case."""
        assert strip_latex_braces("Hello World") == "Hello World"

    def test_strip_braces(self):
        """Test stripping braces from title."""
        result = strip_latex_braces("{CNN} for {NLP}")
        assert result == "CNN for NLP"
        assert "{" not in result
        assert "}" not in result

    def test_strip_preserves_case(self):
        """Test that case is preserved."""
        assert strip_latex_braces("BERT: Pre-Training") == "BERT: Pre-Training"

    def test_strip_preserves_punctuation(self):
        """Test that punctuation is preserved."""
        assert strip_latex_braces("Hello, World!") == "Hello, World!"


class TestCompareTitles:
    """Tests for compare_titles function."""

    def test_exact_match(self):
        """Test exact match returns (True, False) - pass with no warning."""
        exact, warning = compare_titles("Hello World", "Hello World")
        assert exact is True
        assert warning is False

    def test_case_difference_warning(self):
        """Test case difference returns match=True with warning=True."""
        match, warning = compare_titles("Hello World", "hello world")
        assert match is True  # Still a match
        assert warning is True  # But with a warning

    def test_punctuation_mismatch(self):
        """Test punctuation mismatch is a real error."""
        match, warning = compare_titles("Hello World", "Hello World!")
        assert match is False
        assert warning is False  # Real mismatch (fail)

    def test_braces_difference_warning(self):
        """Test that LaTeX brace difference produces warning (not pass)."""
        match, warning = compare_titles("{CNN} for NLP", "CNN for NLP")
        assert match is True  # Still a match
        assert warning is True  # Warning for brace difference (PASS requires exact raw match)

    def test_braces_with_case_difference_warning(self):
        """Test that braces + case difference is match with warning."""
        match, warning = compare_titles("{cnn} for NLP", "CNN for NLP")
        assert match is True  # Still a match
        assert warning is True  # Warning because braces differ (and case)


class TestTitleSimilarity:
    """Tests for title_similarity function."""

    def test_identical_titles(self):
        """Test similarity of identical titles."""
        assert title_similarity("Hello World", "Hello World") == 1.0

    def test_similar_titles(self):
        """Test similarity of similar titles."""
        score = title_similarity("Hello World", "Hello World!")
        assert score > 0.9

    def test_different_titles(self):
        """Test similarity of different titles."""
        score = title_similarity("Hello World", "Goodbye Moon")
        assert score < 0.5


class TestAuthorParsing:
    """Tests for author parsing and comparison functions."""

    def test_normalize_author_name_simple(self):
        """Test normalizing a simple author name (case preserved)."""
        assert normalize_author_name("John Smith") == "John Smith"

    def test_normalize_author_name_last_first(self):
        """Test normalizing 'Last, First' format (case preserved)."""
        assert normalize_author_name("Smith, John") == "John Smith"

    def test_normalize_author_name_with_latex(self):
        """Test normalizing author name with LaTeX (case preserved)."""
        result = normalize_author_name("{John} Smith")
        assert result == "John Smith"

    def test_parse_bibtex_authors_single(self):
        """Test parsing single author."""
        authors = parse_bibtex_authors("John Smith")
        assert authors == ["John Smith"]

    def test_parse_bibtex_authors_multiple(self):
        """Test parsing multiple authors with 'and'."""
        authors = parse_bibtex_authors("John Smith and Jane Doe and Bob Wilson")
        assert len(authors) == 3
        assert authors[0] == "John Smith"
        assert authors[1] == "Jane Doe"
        assert authors[2] == "Bob Wilson"

    def test_parse_bibtex_authors_empty(self):
        """Test parsing empty author field."""
        assert parse_bibtex_authors("") == []

    def test_compare_authors_exact_match(self):
        """Test comparing identical author strings - exact match is PASS."""
        match, warning = compare_authors("John Smith and Jane Doe", ["John Smith", "Jane Doe"])
        assert match is True
        assert warning is False  # Exact match, no warning

    def test_compare_authors_style_difference(self):
        """Test that style differences are WARNING (not PASS)."""
        # "Last, First" format in bibtex vs "First Last" from Semantic Scholar
        match, warning = compare_authors("Smith, John and Doe, Jane", ["John Smith", "Jane Doe"])
        assert match is True
        assert warning is True  # Style difference -> warning

    def test_compare_authors_different_count(self):
        """Test that different author counts are rejected."""
        match, _ = compare_authors("John Smith and Jane Doe", ["John Smith", "Jane Doe", "Bob Wilson"])
        assert match is False

    def test_compare_authors_different_names(self):
        """Test that different names are rejected."""
        match, _ = compare_authors("John Smith and Jane Doe", ["John Smith", "Alice Brown"])
        assert match is False

    def test_compare_authors_abbreviation_rejected(self):
        """Test that abbreviations (M. vs Michael) are NOT allowed."""
        match1, _ = compare_authors("M. Posner", ["Michael Posner"])
        match2, _ = compare_authors("M. I. Posner", ["Michael I. Posner"])
        assert match1 is False
        assert match2 is False

    def test_compare_authors_case_difference_rejected(self):
        """Test that case differences are NOT allowed."""
        match1, _ = compare_authors("john smith", ["John Smith"])
        match2, _ = compare_authors("JOHN SMITH", ["John Smith"])
        assert match1 is False
        assert match2 is False


class TestVenueAliases:
    """Tests for venue alias matching."""

    def test_get_canonical_venue_exact(self):
        """Test getting canonical venue for exact match."""
        assert get_canonical_venue("CoRL") == "CoRL"
        assert get_canonical_venue("NeurIPS") == "NeurIPS"

    def test_get_canonical_venue_full_name(self):
        """Test getting canonical venue for full name."""
        assert get_canonical_venue("Conference on Robot Learning") == "CoRL"
        assert get_canonical_venue("International Conference on Machine Learning") == "ICML"

    def test_get_canonical_venue_unknown(self):
        """Test getting canonical venue for unknown venue."""
        assert get_canonical_venue("Unknown Conference") is None

    def test_venues_match_same(self):
        """Test matching same venue names."""
        assert venues_match("CoRL", "CoRL") is True

    def test_venues_match_alias(self):
        """Test matching venue via alias."""
        assert venues_match("CoRL", "Conference on Robot Learning") is True
        assert venues_match("ICML", "International Conference on Machine Learning") is True

    def test_venues_match_different(self):
        """Test non-matching venues."""
        assert venues_match("CoRL", "ICML") is False
        assert venues_match("Nature", "Science") is False


class TestFieldMismatchDetection:
    """Tests for field mismatch detection."""

    def test_check_year_mismatch(self, make_metadata):
        """Test year mismatch detection."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"year": "2023"}
        metadata = make_metadata(title="Test", year=2024)
        mismatches, warnings = verifier._check_field_mismatches(entry, metadata)
        assert any(m.field_name == "year" for m in mismatches)

    def test_check_year_match(self, make_metadata):
        """Test no failure when years match."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"year": "2024"}
        metadata = make_metadata(title="Test", year=2024)
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "year" for m in mismatches)

    def test_check_venue_mismatch(self, make_metadata):
        """Test venue mismatch detection."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"journal": "Nature"}
        metadata = make_metadata(title="Test", venue="Science")
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert any(m.field_name == "venue" for m in mismatches)

    def test_check_venue_match_alias(self, make_metadata):
        """Test venue match via alias."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"booktitle": "CoRL"}
        metadata = make_metadata(title="Test", venue="Conference on Robot Learning")
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        # Should not fail because "CoRL" is an alias for "Conference on Robot Learning"
        assert not any(m.field_name == "venue" for m in mismatches)

    def test_check_title_mismatch(self, make_metadata):
        """Test title mismatch detection."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"title": "A Completely Different Title"}
        metadata = make_metadata(title="Original Paper Title")
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert any(m.field_name == "title" for m in mismatches)

    def test_check_title_exact_match_pass(self, make_metadata):
        """Test title with exact match is PASS (no warning)."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"title": "CNN for NLP"}
        metadata = make_metadata(title="CNN for NLP")
        mismatches, warnings = verifier._check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "title" for m in mismatches)  # No mismatch
        assert not any(w.field_name == "title" for w in warnings)  # No warning - exact match

    def test_check_title_brace_difference_warning(self, make_metadata):
        """Test title with brace difference is WARNING (not PASS)."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"title": "{CNN} for {NLP}"}
        metadata = make_metadata(title="CNN for NLP")
        mismatches, warnings = verifier._check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "title" for m in mismatches)  # Not a fail
        assert any(w.field_name == "title" for w in warnings)  # Warning for brace difference

    def test_check_title_case_difference_warning(self, make_metadata):
        """Test title with case difference produces warning."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"title": "Learning to Walk"}
        metadata = make_metadata(title="Learning To Walk")
        mismatches, warnings = verifier._check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "title" for m in mismatches)  # Not a fail
        assert any(w.field_name == "title" for w in warnings)  # Warning for case difference

    def test_check_author_mismatch(self, make_metadata):
        """Test author mismatch detection."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"author": "John Smith and Jane Doe"}
        metadata = make_metadata(title="Test", authors=["Alice Brown", "Bob Wilson"])
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert any(m.field_name == "author" for m in mismatches)

    def test_check_author_exact_match(self, make_metadata):
        """Test that author field matches with bibtex 'and' separator."""
        verifier = BibVerifier(skip_verified=True)
        # Bibtex uses "and" separator, metadata returns list
        entry = {"author": "John Smith and Jane Doe"}
        metadata = make_metadata(title="Test", authors=["John Smith", "Jane Doe"])
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "author" for m in mismatches)  # Match

    def test_check_author_style_difference_allowed(self, make_metadata):
        """Test that style differences (Last, First vs First Last) are allowed."""
        verifier = BibVerifier(skip_verified=True)
        # "Last, First" format in bibtex vs "First Last" from metadata
        entry = {"author": "Smith, John and Doe, Jane"}
        metadata = make_metadata(title="Test", authors=["John Smith", "Jane Doe"])
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert not any(m.field_name == "author" for m in mismatches)  # Style difference allowed

    def test_check_author_order_mismatch(self, make_metadata):
        """Test that different author order is a mismatch."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"author": "Jane Doe and John Smith"}  # Different order
        metadata = make_metadata(title="Test", authors=["John Smith", "Jane Doe"])
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert any(m.field_name == "author" for m in mismatches)  # Order matters

    def test_check_author_case_mismatch(self, make_metadata):
        """Test that author case difference is detected as mismatch."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"author": "John smith"}  # lowercase 'smith'
        metadata = make_metadata(title="Test", authors=["John Smith"])
        mismatches, _ = verifier._check_field_mismatches(entry, metadata)
        assert any(m.field_name == "author" for m in mismatches)  # Case mismatch detected


class TestBibVerifier:
    """Tests for BibVerifier class."""

    def test_verifier_init(self):
        """Test verifier initialization."""
        verifier = BibVerifier(skip_verified=True)
        assert verifier.skip_verified is True
        assert verifier._fetcher is not None

    def test_verify_entry_already_verified(self):
        """Test verifying an already verified entry."""
        verifier = BibVerifier(skip_verified=True)
        entry = {"ID": "test2024", "ENTRYTYPE": "article", "title": "Test"}
        content = """
% paper_id: ARXIV:2106.15928, verified via bibtools (2024.12.30)
@article{test2024,
  title = {Test},
  year = {2024}
}
"""
        result = verifier.verify_entry(entry, content)
        assert result.already_verified is True
        assert result.success is True


class TestVerifyEntry:
    """Tests for verify_entry method."""

    def test_verify_entry_no_paper_id(self):
        """Test verify_entry with no paper_id returns warning, not failure."""
        verifier = BibVerifier(skip_verified=True, auto_find_level="none")
        entry = {"ID": "test2024", "title": "Test Paper"}
        content = "@article{test2024, title = {Test Paper}}"

        result = verifier.verify_entry(entry, content)
        assert result.success is True  # Not failure
        assert result.no_paper_id is True

    def test_verify_entry_reverify(self):
        """Test verify_entry with max_age_days=0 re-verifies."""
        verifier = BibVerifier(skip_verified=True, max_age_days=0)
        entry = {"ID": "test2024", "title": "Test", "doi": "10.1234/test"}
        content = """
% paper_id: DOI:10.1234/test, verified via bibtools (2024.12.30)
@article{test2024, title = {Test}, doi = {10.1234/test}}
"""
        result = verifier.verify_entry(entry, content)
        # With max_age_days=0, it should try to re-verify
        assert result.already_verified is not True


class TestShouldSkipVerified:
    """Tests for _should_skip_verified method."""

    def test_max_age_none_always_skips(self):
        """Test max_age_days=None always skips verified entries."""
        verifier = BibVerifier(skip_verified=True, max_age_days=None)
        assert verifier._should_skip_verified("2020.01.01") is True
        assert verifier._should_skip_verified("2025.01.01") is True
        assert verifier._should_skip_verified(None) is True

    def test_max_age_zero_never_skips(self):
        """Test max_age_days=0 never skips (always re-verify)."""
        verifier = BibVerifier(skip_verified=True, max_age_days=0)
        assert verifier._should_skip_verified("2020.01.01") is False
        assert verifier._should_skip_verified("2025.01.01") is False
        assert verifier._should_skip_verified(None) is False

    def test_max_age_with_old_date(self):
        """Test max_age_days with old verification date."""
        verifier = BibVerifier(skip_verified=True, max_age_days=30)
        # Very old date should NOT skip (re-verify)
        assert verifier._should_skip_verified("2020.01.01") is False

    def test_max_age_with_recent_date(self):
        """Test max_age_days with recent verification date."""
        from datetime import datetime, timedelta

        verifier = BibVerifier(skip_verified=True, max_age_days=30)
        # Recent date should skip
        recent = (datetime.now() - timedelta(days=5)).strftime("%Y.%m.%d")
        assert verifier._should_skip_verified(recent) is True

    def test_max_age_with_invalid_date(self):
        """Test max_age_days with invalid date format."""
        verifier = BibVerifier(skip_verified=True, max_age_days=30)
        # Invalid date should NOT skip (re-verify)
        assert verifier._should_skip_verified("invalid") is False
        assert verifier._should_skip_verified("2024-01-01") is False  # Wrong format


class TestVerifierIntegration:
    """Integration tests for verifier."""

    def test_verify_file_already_verified(self, tmp_path):
        """Test verifying file with already verified entries."""
        bib_content = """
% paper_id: ARXIV:2106.15928, verified via bibtools (2024.01.01)
@article{test2024,
  title = {Test Paper},
  author = {Author},
  year = {2024}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)

        verifier = BibVerifier(skip_verified=True)
        report, _ = verifier.verify_file(bib_file)

        # Entry is already verified
        assert report.already_verified == 1
        assert report.total_entries == 1

    def test_verify_file_multiple_entries(self, tmp_path):
        """Test verifying file with multiple entries."""
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

        verifier = BibVerifier(skip_verified=True, auto_find_level="none")
        report, _ = verifier.verify_file(bib_file)

        assert report.total_entries == 2
        assert report.already_verified == 1
        # Second entry has no paper_id
        assert report.no_paper_id == 1


class TestVerifierWithMockAPI:
    """Tests for verifier with mocked API."""

    def test_verify_entry_with_doi_success(self, make_metadata):
        """Test verify_entry successfully verifies paper via DOI."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, auto_find_level="id")
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith"],
            year=2024,
            venue="NeurIPS",
            doi="10.1234/test",
        )
        # Mock batch resolve and fetch_with_resolved (unified path)
        resolved = ResolvedIds(
            paper_id="DOI:10.1234/test",
            doi="10.1234/test",
            arxiv_id=None,
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/test": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        entry = {
            "ID": "smith2024test",
            "title": "Test Paper",
            "author": "John Smith",
            "year": "2024",
            "doi": "10.1234/test",
        }
        content = "@article{smith2024test, title = {Test Paper}}"

        result = verifier.verify_entry(entry, content)
        assert result.success is True
        assert result.paper_id_used == "DOI:10.1234/test"

    def test_verify_entry_api_error(self):
        """Test verify_entry handles API error."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, auto_find_level="id")
        resolved = ResolvedIds(
            paper_id="DOI:10.1234/test",
            doi="10.1234/test",
            arxiv_id=None,
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/test": resolved})
        verifier._fetch_with_resolved = MagicMock(side_effect=ConnectionError("API unavailable"))

        entry = {"ID": "test2024", "doi": "10.1234/test"}
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        assert result.success is False
        assert "API error" in result.message

    def test_verify_entry_paper_not_found(self):
        """Test verify_entry when paper is not found."""
        verifier = BibVerifier(skip_verified=True, auto_find_level="id")
        # S2 batch returns None for this paper_id
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/nonexistent": None})

        entry = {"ID": "test2024", "doi": "10.1234/nonexistent"}
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        assert result.success is False
        assert "Paper not found" in result.message

    def test_verify_entry_field_mismatch(self, make_metadata):
        """Test verify_entry detects field mismatch."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, auto_find_level="id", fix_errors=False)
        metadata = make_metadata(
            title="Correct Title",
            authors=["John Smith"],
            year=2025,  # Different year
        )
        resolved = ResolvedIds(
            paper_id="DOI:10.1234/test",
            doi="10.1234/test",
            arxiv_id=None,
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/test": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        entry = {
            "ID": "test2024",
            "title": "Correct Title",
            "year": "2024",  # Wrong year
            "doi": "10.1234/test",
        }
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        assert result.success is False
        assert "year" in result.message
        assert len(result.mismatches) > 0

    def test_verify_entry_fix_mode(self, make_metadata):
        """Test verify_entry with fix_errors=True."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, auto_find_level="id", fix_errors=True)
        metadata = make_metadata(
            title="Correct Title",
            authors=["John Smith"],
            year=2025,
        )
        resolved = ResolvedIds(
            paper_id="DOI:10.1234/test",
            doi="10.1234/test",
            arxiv_id=None,
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/test": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        entry = {
            "ID": "test2024",
            "title": "Correct Title",
            "year": "2024",  # Wrong year - should be fixed
            "doi": "10.1234/test",  # This provides paper_id
        }
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        assert result.success is True
        assert result.fixed is True
        assert len(result.mismatches) > 0

    def test_verify_file_with_mock_success(self, tmp_path, make_metadata):
        """Test verify_file with mocked API for successful verification."""
        from bibtools.semantic_scholar import ResolvedIds

        bib_content = """@article{test2024,
  doi = {10.1234/example},
  title = {Test Paper},
  author = {Smith, John},
  year = {2024}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)

        verifier = BibVerifier(skip_verified=True)
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith"],  # Will become {"given": "John", "family": "Smith"} -> "Smith, John"
            year=2024,
            venue="NeurIPS",
            doi="10.1234/example",
        )
        # Mock batch resolve and fetch_with_resolved for verify_file
        resolved = ResolvedIds(
            paper_id="DOI:10.1234/example",
            doi="10.1234/example",
            arxiv_id=None,
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/example": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        report, updated_content = verifier.verify_file(bib_file)

        assert report.verified == 1
        # New format: "% paper_id: {id}, verified via bibtools ({date})"
        assert "% paper_id: DOI:10.1234/example, verified via bibtools" in updated_content

    def test_warning_adds_paper_id_only(self, tmp_path, make_metadata):
        """Test that WARNING results add paper_id but NOT 'verified via'.

        WARNING means format differs but paper is correctly identified.
        paper_id is written for identification, but "verified via" is omitted
        so the entry will be re-checked on future runs.
        """
        from bibtools.semantic_scholar import ResolvedIds

        bib_content = """% paper_id: ARXIV:1234.5678
@article{test2024,
  title = {test paper with lowercase},
  author = {John Smith},
  year = {2024}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)

        verifier = BibVerifier(skip_verified=False)
        # API returns title with different case -> WARNING
        metadata = make_metadata(
            title="Test Paper With Lowercase",  # Different case
            authors=["John Smith"],
            year=2024,
        )
        # Mock batch resolve and fetch_with_resolved for verify_file
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        report, updated_content = verifier.verify_file(bib_file)

        # Should be a warning (case difference)
        assert report.verified_with_warnings == 1
        assert report.verified == 0
        # WARNING adds paper_id only (no "verified via")
        assert "% paper_id: ARXIV:1234.5678\n" in updated_content
        assert "verified via" not in updated_content

    def test_pass_adds_verified_comment(self, tmp_path, make_metadata):
        """Test that PASS results DO add 'verified via' comment."""
        from bibtools.semantic_scholar import ResolvedIds

        bib_content = """% paper_id: ARXIV:1234.5678
@article{test2024,
  title = {Test Paper},
  author = {Smith, John},
  year = {2024}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(bib_content)

        verifier = BibVerifier(skip_verified=False)
        # API returns exact match -> PASS (bibtex uses "Smith, John" format)
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith"],  # -> {"given": "John", "family": "Smith"} -> "Smith, John"
            year=2024,
        )
        # Mock batch resolve and fetch_with_resolved for verify_file
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        report, updated_content = verifier.verify_file(bib_file)

        # Should be a pass
        assert report.verified == 1
        assert report.verified_with_warnings == 0
        # "verified via" SHOULD be added
        assert "verified via bibtools" in updated_content


class TestArxivCrossCheck:
    """Tests for arXiv cross-check feature."""

    def test_arxiv_cross_check_disabled(self, make_metadata):
        """Test that arxiv_check=False skips cross-check."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, arxiv_check=False)
        # Different authors in metadata vs arxiv (would fail if checked)
        metadata = make_metadata(
            title="Test Paper",
            authors=["Wrong Author"],  # Different from arXiv
            year=2024,
            source="dblp",
        )
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id="conf/neurips/Test2024",
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        entry = {
            "ID": "test2024",
            "title": "Test Paper",
            "author": "Wrong Author",
            "year": "2024",
            "eprint": "1234.5678",
        }
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        # Should pass because arxiv_check is disabled
        assert result.success is True

    def test_arxiv_cross_check_authors_match(self, make_metadata):
        """Test arxiv cross-check passes when authors match."""
        from unittest.mock import patch

        from bibtools.fetcher import ArxivMetadata
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, arxiv_check=True)
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith", "Jane Doe"],
            year=2024,
            source="dblp",
        )
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id="conf/neurips/Test2024",
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        # Mock arXiv client to return same authors
        arxiv_meta = ArxivMetadata(
            title="Test Paper",
            authors=[{"given": "John", "family": "Smith"}, {"given": "Jane", "family": "Doe"}],
            year=2024,
            arxiv_id="1234.5678",
        )
        with patch.object(verifier._fetcher.arxiv_client, "get_paper_metadata", return_value=arxiv_meta):
            entry = {
                "ID": "test2024",
                "title": "Test Paper",
                "author": "Smith, John and Doe, Jane",
                "year": "2024",
                "eprint": "1234.5678",
            }
            content = "@article{test2024}"

            result = verifier.verify_entry(entry, content)
            assert result.success is True

    def test_arxiv_cross_check_authors_mismatch(self, make_metadata):
        """Test arxiv cross-check fails when authors mismatch."""
        from unittest.mock import patch

        from bibtools.fetcher import ArxivMetadata
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, arxiv_check=True)
        # DBLP returns wrong authors (this can happen with OpenVLA case)
        metadata = make_metadata(
            title="Test Paper",
            authors=["Wrong Author", "Another Wrong"],
            year=2024,
            source="dblp",
        )
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id="conf/neurips/Test2024",
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        # Mock arXiv client to return different (correct) authors
        arxiv_meta = ArxivMetadata(
            title="Test Paper",
            authors=[{"given": "John", "family": "Smith"}, {"given": "Jane", "family": "Doe"}],
            year=2024,
            arxiv_id="1234.5678",
        )
        with patch.object(verifier._fetcher.arxiv_client, "get_paper_metadata", return_value=arxiv_meta):
            entry = {
                "ID": "test2024",
                "title": "Test Paper",
                "author": "Wrong Author and Another Wrong",
                "year": "2024",
                "eprint": "1234.5678",
            }
            content = "@article{test2024}"

            result = verifier.verify_entry(entry, content)
            assert result.success is False
            assert "arXiv cross-check failed" in result.message
            assert "authors mismatch" in result.message

    def test_arxiv_cross_check_skipped_for_arxiv_source(self, make_metadata):
        """Test arxiv cross-check is skipped when source is arxiv."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, arxiv_check=True)
        # Source is arxiv itself, no cross-check needed
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith"],
            year=2024,
            source="arxiv",  # Source is arxiv
        )
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        entry = {
            "ID": "test2024",
            "title": "Test Paper",
            "author": "Smith, John",
            "year": "2024",
            "eprint": "1234.5678",
        }
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        # Should pass - no cross-check for arxiv source
        assert result.success is True

    def test_arxiv_cross_check_no_arxiv_id(self, make_metadata):
        """Test arxiv cross-check is skipped when no arxiv_id."""
        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, arxiv_check=True)
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith"],
            year=2024,
            source="crossref",
        )
        resolved = ResolvedIds(
            paper_id="DOI:10.1234/test",
            doi="10.1234/test",
            arxiv_id=None,  # No arxiv ID
            dblp_id=None,
        )
        verifier._resolve_batch = MagicMock(return_value={"DOI:10.1234/test": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        entry = {
            "ID": "test2024",
            "title": "Test Paper",
            "author": "Smith, John",
            "year": "2024",
            "doi": "10.1234/test",
        }
        content = "@article{test2024}"

        result = verifier.verify_entry(entry, content)
        # Should pass - no arxiv_id to cross-check
        assert result.success is True

    def test_arxiv_cross_check_api_error_continues(self, make_metadata):
        """Test that arxiv API error does not fail verification."""
        from unittest.mock import patch

        from bibtools.semantic_scholar import ResolvedIds

        verifier = BibVerifier(skip_verified=True, arxiv_check=True)
        metadata = make_metadata(
            title="Test Paper",
            authors=["John Smith"],
            year=2024,
            source="dblp",
        )
        resolved = ResolvedIds(
            paper_id="ARXIV:1234.5678",
            doi=None,
            arxiv_id="1234.5678",
            dblp_id="conf/neurips/Test2024",
        )
        verifier._resolve_batch = MagicMock(return_value={"ARXIV:1234.5678": resolved})
        verifier._fetch_with_resolved = MagicMock(return_value=metadata)

        # Mock arXiv client to raise exception
        with patch.object(
            verifier._fetcher.arxiv_client,
            "get_paper_metadata",
            side_effect=Exception("arXiv API error"),
        ):
            entry = {
                "ID": "test2024",
                "title": "Test Paper",
                "author": "Smith, John",
                "year": "2024",
                "eprint": "1234.5678",
            }
            content = "@article{test2024}"

            result = verifier.verify_entry(entry, content)
            # Should pass - arxiv error doesn't fail verification
            assert result.success is True

"""Tests for bibtex parser."""

from bibtools.parser import (
    extract_paper_id_from_comments,
    extract_paper_id_from_entry,
    generate_verification_comment,
    is_entry_verified,
    parse_bib_file,
)


class TestParseBibFile:
    """Tests for parse_bib_file function."""

    def test_parse_single_entry(self, tmp_path):
        """Test parsing a single bibtex entry."""
        content = """
@article{test2024,
  title = {Test Paper Title},
  author = {John Doe},
  year = {2024}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(content)
        entries, raw = parse_bib_file(bib_file)
        assert len(entries) == 1
        assert entries[0]["ID"] == "test2024"
        assert entries[0]["title"] == "Test Paper Title"
        assert entries[0]["author"] == "John Doe"
        assert entries[0]["year"] == "2024"

    def test_parse_multiple_entries(self, tmp_path):
        """Test parsing multiple bibtex entries."""
        content = """
@article{first2024,
  title = {First Paper},
  author = {Author One},
  year = {2024}
}

@inproceedings{second2023,
  title = {Second Paper},
  author = {Author Two},
  booktitle = {Some Conference},
  year = {2023}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(content)
        entries, _ = parse_bib_file(bib_file)
        assert len(entries) == 2
        assert entries[0]["ID"] == "first2024"
        assert entries[1]["ID"] == "second2023"

    def test_parse_entry_with_arxiv(self, tmp_path):
        """Test parsing entry with arXiv ID in eprint field."""
        content = """
@article{arxiv2024,
  title = {ArXiv Paper},
  author = {Researcher},
  year = {2024},
  eprint = {2406.09246},
  archiveprefix = {arXiv}
}
"""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text(content)
        entries, _ = parse_bib_file(bib_file)
        assert len(entries) == 1
        assert entries[0]["eprint"] == "2406.09246"


class TestIsEntryVerified:
    """Tests for is_entry_verified function."""

    def test_is_entry_verified_via_bibtools(self):
        """Test detecting bibtools verification comment."""
        content = """
% paper_id: ARXIV:2106.15928, verified via bibtools (2024.12.30)
@article{test2024,
  title = {Test Paper},
  year = {2024}
}
"""
        is_verified, date_str, paper_id = is_entry_verified(content, "test2024")
        assert is_verified is True
        assert date_str == "2024.12.30"
        assert paper_id == "ARXIV:2106.15928"

    def test_is_entry_verified_via_human(self):
        """Test detecting human verification comment."""
        content = """
% paper_id: DOI:10.1234/example, verified via human(홍길동) (2024.12.30)
@article{test2024,
  title = {Test Paper},
  year = {2024}
}
"""
        is_verified, date_str, paper_id = is_entry_verified(content, "test2024")
        assert is_verified is True
        assert date_str == "2024.12.30"
        assert paper_id == "DOI:10.1234/example"

    def test_is_entry_unverified_paper_id_only(self):
        """Test that paper_id without verification is NOT verified."""
        content = """
% paper_id: ARXIV:2106.15928
@article{test2024,
  title = {Test Paper},
  year = {2024}
}
"""
        is_verified, date_str, paper_id = is_entry_verified(content, "test2024")
        assert is_verified is False
        assert date_str is None
        assert paper_id == "ARXIV:2106.15928"

    def test_is_entry_verified_false(self):
        """Test when no paper_id comment exists."""
        content = """
% Some other comment
@article{test2024,
  title = {Test Paper},
  year = {2024}
}
"""
        is_verified, _, _ = is_entry_verified(content, "test2024")
        assert is_verified is False

    def test_legacy_format_not_recognized(self):
        """Test that legacy formats are NOT recognized."""
        # Old format - should NOT be recognized
        content = """
% Verified via bibtools (2024.12.30) - paper_id: ARXIV:2106.15928
@article{test2024,
  title = {Test Paper},
  year = {2024}
}
"""
        is_verified, _, _ = is_entry_verified(content, "test2024")
        assert is_verified is False


class TestGenerateVerificationComment:
    """Tests for generate_verification_comment function."""

    def test_generate_with_arxiv(self):
        """Test generating comment with arXiv paper_id."""
        comment = generate_verification_comment("ARXIV:2106.15928")
        # Format: "% paper_id: {id}, verified via bibtools@x.y.z (YYYY.MM.DD)"
        assert comment.startswith("% paper_id: ARXIV:2106.15928")
        assert ", verified via bibtools " in comment
        # Should be single line
        assert "\n" not in comment

    def test_generate_with_doi(self):
        """Test generating comment with DOI paper_id."""
        comment = generate_verification_comment("DOI:10.1234/example")
        assert comment.startswith("% paper_id: DOI:10.1234/example")
        assert ", verified via bibtools " in comment


class TestExtractPaperId:
    """Tests for paper_id extraction functions."""

    def test_extract_from_verified_comment(self):
        """Test extracting paper_id from verified comment."""
        content = """% paper_id: ARXIV:2106.15928, verified via bibtools (2024.12.30)
@inproceedings{test2024,
  title = {Test Paper},
}
"""
        paper_id = extract_paper_id_from_comments(content, "test2024")
        assert paper_id == "ARXIV:2106.15928"

    def test_extract_from_unverified_comment(self):
        """Test extracting paper_id from unverified comment (paper_id only)."""
        content = """% paper_id: ARXIV:2106.15928
@inproceedings{test2024,
  title = {Test Paper},
}
"""
        paper_id = extract_paper_id_from_comments(content, "test2024")
        assert paper_id == "ARXIV:2106.15928"

    def test_extract_from_human_verified_comment(self):
        """Test extracting paper_id from human-verified comment."""
        content = """% paper_id: DOI:10.1234/example, verified via human(홍길동) (2024.12.30)
@article{test2024,
  title = {Test Paper},
}
"""
        paper_id = extract_paper_id_from_comments(content, "test2024")
        assert paper_id == "DOI:10.1234/example"

    def test_extract_no_comment(self):
        """Test when no paper_id comment exists."""
        content = """% Some other comment
@article{test2024,
  title = {Test Paper},
}
"""
        paper_id = extract_paper_id_from_comments(content, "test2024")
        assert paper_id is None

    def test_extract_from_doi_field(self):
        """Test extracting paper_id from DOI field."""
        entry = {"ID": "test2024", "doi": "10.18653/v1/N18-3011"}
        content = "@inproceedings{test2024, title = {Test}}"
        paper_id, source = extract_paper_id_from_entry(entry, content)
        assert paper_id == "DOI:10.18653/v1/N18-3011"
        assert source == "doi"

    def test_extract_from_eprint_field(self):
        """Test extracting paper_id from eprint field."""
        entry = {"ID": "test2024", "eprint": "2106.15928"}
        content = "@inproceedings{test2024, title = {Test}}"
        paper_id, source = extract_paper_id_from_entry(entry, content)
        assert paper_id == "ARXIV:2106.15928"
        assert source == "eprint"

    def test_comment_priority_over_doi(self):
        """Test that comment paper_id takes priority over DOI field."""
        entry = {"ID": "test2024", "doi": "10.18653/v1/N18-3011"}
        content = """% paper_id: ARXIV:2106.15928, verified via bibtools (2024.12.30)
@inproceedings{test2024, title = {Test}}
"""
        paper_id, source = extract_paper_id_from_entry(entry, content)
        assert paper_id == "ARXIV:2106.15928"
        assert source == "comment"

    def test_unverified_comment_priority_over_doi(self):
        """Test that unverified comment paper_id takes priority over DOI field."""
        entry = {"ID": "test2024", "doi": "10.18653/v1/N18-3011"}
        content = """% paper_id: ARXIV:2106.15928
@inproceedings{test2024, title = {Test}}
"""
        paper_id, source = extract_paper_id_from_entry(entry, content)
        assert paper_id == "ARXIV:2106.15928"
        assert source == "comment"

    def test_no_paper_id(self):
        """Test when no paper_id is found."""
        entry = {"ID": "test2024", "title": "Test"}
        content = "@inproceedings{test2024, title = {Test}}"
        paper_id, source = extract_paper_id_from_entry(entry, content)
        assert paper_id is None
        assert source is None

    def test_auto_find_level_none(self):
        """Test that auto_find_level='none' only checks comments."""
        entry = {"ID": "test2024", "doi": "10.18653/v1/N18-3011"}
        content = "@inproceedings{test2024, title = {Test}}"
        paper_id, source = extract_paper_id_from_entry(entry, content, auto_find_level="none")
        assert paper_id is None
        assert source is None

    def test_auto_find_level_none_with_comment(self):
        """Test that auto_find_level='none' still works with comment."""
        entry = {"ID": "test2024", "doi": "10.18653/v1/N18-3011"}
        content = """% paper_id: ARXIV:2106.15928
@inproceedings{test2024, title = {Test}}
"""
        paper_id, source = extract_paper_id_from_entry(entry, content, auto_find_level="none")
        assert paper_id == "ARXIV:2106.15928"
        assert source == "comment"

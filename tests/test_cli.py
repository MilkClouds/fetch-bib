"""Tests for CLI module."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bibtools import __version__
from bibtools.cli import app
from bibtools.models import VerificationReport, VerificationResult

runner = CliRunner()


class TestVersionCommand:
    """Tests for version option."""

    def test_version_option(self):
        """Test --version option."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_option(self):
        """Test -V option."""
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestVerifyCommand:
    """Tests for verify command."""

    def test_verify_nonexistent_file(self):
        """Test verify with non-existent file."""
        result = runner.invoke(app, ["verify", "nonexistent.bib"])
        assert result.exit_code != 0

    def test_verify_invalid_auto_find(self, tmp_path):
        """Test verify with invalid --auto-find option."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        result = runner.invoke(app, ["verify", str(bib_file), "--auto-find=invalid"])
        assert result.exit_code == 1
        assert "Invalid --auto-find level" in result.output

    def test_verify_fix_errors_without_none(self, tmp_path):
        """Test that --fix-errors requires --auto-find=none."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        result = runner.invoke(app, ["verify", str(bib_file), "--fix-errors"])
        assert result.exit_code == 1
        assert "--fix-errors/--fix-warnings only allowed with --auto-find=none" in result.output

    def test_verify_fix_warnings_without_none(self, tmp_path):
        """Test that --fix-warnings requires --auto-find=none."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        result = runner.invoke(app, ["verify", str(bib_file), "--fix-warnings"])
        assert result.exit_code == 1
        assert "--fix-errors/--fix-warnings only allowed with --auto-find=none" in result.output

    @patch("bibtools.cli.BibVerifier")
    def test_verify_dry_run(self, mock_verifier_class, tmp_path):
        """Test verify with --dry-run option."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        # Setup mock
        mock_verifier = MagicMock()
        mock_verifier_class.return_value = mock_verifier
        report = VerificationReport()
        mock_verifier.verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["verify", str(bib_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    @patch("bibtools.cli.BibVerifier")
    def test_verify_already_verified(self, mock_verifier_class, tmp_path):
        """Test verify with already verified entries."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_verifier = MagicMock()
        mock_verifier_class.return_value = mock_verifier
        report = VerificationReport()
        result_entry = VerificationResult(
            entry_key="test",
            success=True,
            message="Already verified",
            already_verified=True,
        )
        report.add_result(result_entry)
        mock_verifier.verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["verify", str(bib_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Already verified: 1" in result.output

    @patch("bibtools.cli.BibVerifier")
    def test_verify_max_age_option(self, mock_verifier_class, tmp_path):
        """Test verify with --max-age option."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_verifier = MagicMock()
        mock_verifier_class.return_value = mock_verifier
        report = VerificationReport()
        mock_verifier.verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["verify", str(bib_file), "--max-age=90", "--dry-run"])
        assert result.exit_code == 0
        assert "older than 90 days" in result.output
        # Verify BibVerifier was called with max_age_days=90
        mock_verifier_class.assert_called_once()
        call_kwargs = mock_verifier_class.call_args[1]
        assert call_kwargs["max_age_days"] == 90

    @patch("bibtools.cli.BibVerifier")
    def test_verify_reverify_equals_max_age_zero(self, mock_verifier_class, tmp_path):
        """Test that --reverify is equivalent to --max-age=0."""
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_verifier = MagicMock()
        mock_verifier_class.return_value = mock_verifier
        report = VerificationReport()
        mock_verifier.verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["verify", str(bib_file), "--reverify", "--dry-run"])
        assert result.exit_code == 0
        assert "--reverify or --max-age=0" in result.output
        # Verify BibVerifier was called with max_age_days=0
        mock_verifier_class.assert_called_once()
        call_kwargs = mock_verifier_class.call_args[1]
        assert call_kwargs["max_age_days"] == 0


class TestFetchCommand:
    """Tests for fetch command."""

    @patch("bibtools.cli.BibtexGenerator")
    def test_fetch_success(self, mock_generator_class):
        """Test successful paper fetch."""
        from bibtools.models import FetchResult, PaperMetadata

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        metadata = PaperMetadata(
            title="Test Paper Title",
            authors=[{"given": "John", "family": "Smith"}, {"given": "Jane", "family": "Doe"}],
            year=2024,
            venue="NeurIPS",
            source="crossref",
        )
        bibtex = "@article{smith2024test, title = {Test Paper Title}}"
        mock_generator.fetch_by_paper_id.return_value = FetchResult(bibtex=bibtex, metadata=metadata)

        result = runner.invoke(app, ["fetch", "ARXIV:2106.15928"])
        assert result.exit_code == 0
        assert "Test Paper Title" in result.output
        assert "John Smith" in result.output

    @patch("bibtools.cli.BibtexGenerator")
    def test_fetch_not_found(self, mock_generator_class):
        """Test fetch with paper not found."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.fetch_by_paper_id.return_value = None

        result = runner.invoke(app, ["fetch", "ARXIV:0000.00000"])
        assert result.exit_code == 1
        assert "Paper not found" in result.output


class TestSearchCommand:
    """Tests for search command."""

    @patch("bibtools.cli.BibtexGenerator")
    def test_search_success(self, mock_generator_class):
        """Test successful paper search."""
        from bibtools.models import FetchResult, PaperMetadata

        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        metadata = PaperMetadata(
            title="Machine Learning Paper",
            authors=[{"given": "Author", "family": "One"}],
            year=2024,
            venue="NeurIPS",
            source="crossref",
        )
        mock_generator.search_by_query.return_value = [
            FetchResult(bibtex="@article{one2024ml}", metadata=metadata),
        ]

        result = runner.invoke(app, ["search", "machine learning"])
        assert result.exit_code == 0
        assert "Machine Learning Paper" in result.output
        assert "WARNING" in result.output  # Safety warning

    @patch("bibtools.cli.BibtexGenerator")
    def test_search_no_results(self, mock_generator_class):
        """Test search with no results."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.search_by_query.return_value = []

        result = runner.invoke(app, ["search", "nonexistent paper xyz"])
        assert result.exit_code == 1
        assert "No results found" in result.output

    @patch("bibtools.cli.BibtexGenerator")
    def test_search_with_limit(self, mock_generator_class):
        """Test search with --limit option."""
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator
        mock_generator.search_by_query.return_value = []

        runner.invoke(app, ["search", "test", "--limit", "3"])
        mock_generator.search_by_query.assert_called_once_with("test", limit=3)

"""Tests for CLI module."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bibtools import __version__
from bibtools.cli import app
from bibtools.models import ResolveReport, ResolveResult, VerificationReport

runner = CliRunner()


class TestVersionCommand:
    def test_version_option(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_option(self):
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestVerifyCommand:
    def test_verify_nonexistent_file(self):
        result = runner.invoke(app, ["verify", "nonexistent.bib"])
        assert result.exit_code != 0

    @patch("bibtools.cli.verify_file")
    @patch("bibtools.cli.MetadataFetcher")
    def test_verify_max_age_option(self, mock_fetcher_class, mock_verify_file, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        report = VerificationReport()
        mock_verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["verify", str(bib_file), "--max-age=90"])
        assert result.exit_code == 0
        assert "older than 90 days" in result.output
        mock_verify_file.assert_called_once()

    @patch("bibtools.cli.verify_file")
    @patch("bibtools.cli.MetadataFetcher")
    def test_verify_reverify_equals_max_age_zero(self, mock_fetcher_class, mock_verify_file, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        report = VerificationReport()
        mock_verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["verify", str(bib_file), "--reverify"])
        assert result.exit_code == 0
        assert "--reverify or --max-age=0" in result.output
        mock_verify_file.assert_called_once()


class TestResolveCommand:
    @patch("bibtools.cli.BibResolver")
    def test_resolve_dry_run(self, mock_resolver_class, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_resolver = MagicMock()
        mock_resolver_class.return_value = mock_resolver
        report = ResolveReport()
        report.add_result(
            ResolveResult(
                entry_key="test",
                success=True,
                message="Resolved",
                paper_id="ARXIV:2106.15928",
                source="title",
                confidence=0.95,
            )
        )
        mock_resolver.resolve_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["resolve", str(bib_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Resolved" in result.output
        assert "Dry run" in result.output


class TestReviewCommand:
    @patch("bibtools.cli.verify_file")
    @patch("bibtools.cli.MetadataFetcher")
    def test_review_no_changes(self, mock_fetcher_class, mock_verify_file, tmp_path):
        bib_file = tmp_path / "test.bib"
        bib_file.write_text("@article{test, title = {Test}}")

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        report = VerificationReport()
        mock_verify_file.return_value = (report, "@article{test}")

        result = runner.invoke(app, ["review", str(bib_file), "--verified-via", "human"])
        assert result.exit_code == 0
        assert "No changes applied" in result.output


class TestFetchCommand:
    @patch("bibtools.cli.MetadataFetcher")
    def test_fetch_success(self, mock_fetcher_class):
        from bibtools.models import FetchBundle, PaperMetadata

        metadata = PaperMetadata(
            title="Test Paper Title",
            authors=[{"given": "John", "family": "Smith"}, {"given": "Jane", "family": "Doe"}],
            year=2024,
            venue="NeurIPS",
            source="crossref",
        )
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.fetch_bundle.return_value = FetchBundle(
            selected=metadata,
            sources={"crossref": metadata},
            arxiv_conflict=False,
        )

        result = runner.invoke(app, ["fetch", "ARXIV:2106.15928"])
        assert result.exit_code == 0
        assert "Test Paper Title" in result.output
        assert "John Smith" in result.output

    @patch("bibtools.cli.MetadataFetcher")
    def test_fetch_not_found(self, mock_fetcher_class):
        from bibtools.models import FetchBundle

        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.fetch_bundle.return_value = FetchBundle(
            selected=None,
            sources={},
            arxiv_conflict=False,
        )

        result = runner.invoke(app, ["fetch", "ARXIV:0000.00000"])
        assert result.exit_code == 1
        assert "Paper not found" in result.output


class TestSearchCommand:
    @patch("bibtools.cli.MetadataFetcher")
    def test_search_success(self, mock_fetcher_class):
        from bibtools.models import PaperMetadata
        from bibtools.models import FetchBundle
        from bibtools.semantic_scholar import ResolvedIds

        metadata = PaperMetadata(
            title="Machine Learning Paper",
            authors=[{"given": "Author", "family": "One"}],
            year=2024,
            venue="NeurIPS",
            source="crossref",
        )
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.s2_client.search_by_title.return_value = [
            ResolvedIds(
                paper_id="paper1", doi="10.1/a", arxiv_id=None, dblp_id=None, venue="NeurIPS", title="ML Paper"
            ),
        ]
        mock_fetcher.fetch_bundle_with_resolved.return_value = FetchBundle(
            selected=metadata,
            sources={"crossref": metadata},
            arxiv_conflict=False,
        )

        result = runner.invoke(app, ["search", "machine learning"])
        assert result.exit_code == 0
        assert "Machine Learning Paper" in result.output
        assert "WARNING" in result.output

    @patch("bibtools.cli.MetadataFetcher")
    def test_search_no_results(self, mock_fetcher_class):
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.s2_client.search_by_title.return_value = []

        result = runner.invoke(app, ["search", "nonexistent paper xyz"])
        assert result.exit_code == 1
        assert "No results found" in result.output

    @patch("bibtools.cli.MetadataFetcher")
    def test_search_with_limit(self, mock_fetcher_class):
        mock_fetcher = MagicMock()
        mock_fetcher_class.return_value = mock_fetcher
        mock_fetcher.s2_client.search_by_title.return_value = []

        runner.invoke(app, ["search", "test", "--limit", "3"])
        mock_fetcher.s2_client.search_by_title.assert_called_once_with("test", limit=3)

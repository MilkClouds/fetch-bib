"""Paper ID resolver for bibtex entries."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from .models import ResolveReport, ResolveResult
from .parser import extract_paper_id_from_comments, insert_paper_id_comment, parse_bib_file
from .semantic_scholar import SemanticScholarClient
from .utils import title_similarity


class BibResolver:
    """Resolve paper_id for bibtex entries and add comments."""

    def __init__(
        self,
        api_key: str | None = None,
        min_confidence: float = 0.85,
        console: Console | None = None,
        *,
        s2_client: SemanticScholarClient | None = None,
    ) -> None:
        self.min_confidence = min_confidence
        self.console = console or Console()
        self._s2_client = s2_client or SemanticScholarClient(api_key=api_key)
        self._owns_client = s2_client is None

    def close(self) -> None:
        """Close owned client."""
        if self._owns_client:
            self._s2_client.close()

    def __enter__(self) -> "BibResolver":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def resolve_file(self, file_path: Path) -> tuple[ResolveReport, str]:
        """Resolve paper_ids for a bibtex file.

        Args:
            file_path: Path to the .bib file.

        Returns:
            Tuple of (resolve report, updated content).
        """
        entries, content = parse_bib_file(file_path)
        updated_content = content
        report = ResolveReport()

        for entry in entries:
            entry_key = entry.get("ID", "unknown")

            # Skip if already has paper_id comment
            existing = extract_paper_id_from_comments(content, entry_key)
            if existing:
                report.add_result(
                    ResolveResult(
                        entry_key=entry_key,
                        success=True,
                        message="Already has paper_id",
                        paper_id=existing,
                        source="comment",
                        confidence=1.0,
                        already_has_paper_id=True,
                    )
                )
                continue

            result = self._resolve_entry(entry)
            report.add_result(result)

            if result.success and result.paper_id:
                extra = []
                if result.confidence is not None:
                    extra.append(
                        f"paper_id_confidence: {result.confidence:.2f} (source: {result.source or 'unknown'})"
                    )
                updated_content = insert_paper_id_comment(
                    updated_content,
                    entry_key,
                    result.paper_id,
                    include_verified=False,
                    extra_comments=extra,
                )
                result.updated = True

        return report, updated_content

    def _resolve_entry(self, entry: dict) -> ResolveResult:
        """Resolve paper_id for a single entry."""
        entry_key = entry.get("ID", "unknown")

        doi = entry.get("doi", "")
        if doi:
            clean_doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
            return ResolveResult(
                entry_key=entry_key,
                success=True,
                message="Resolved from doi field",
                paper_id=f"DOI:{clean_doi}",
                source="doi",
                confidence=1.0,
            )

        eprint = entry.get("eprint", "")
        if eprint:
            clean_eprint = eprint.replace("arXiv:", "").strip()
            return ResolveResult(
                entry_key=entry_key,
                success=True,
                message="Resolved from eprint field",
                paper_id=f"ARXIV:{clean_eprint}",
                source="eprint",
                confidence=1.0,
            )

        title = entry.get("title", "")
        if not title:
            return ResolveResult(
                entry_key=entry_key,
                success=False,
                message="No title or IDs available for resolution",
            )

        try:
            resolved_list = self._s2_client.search_by_title(title, limit=5)
        except ConnectionError as exc:
            return ResolveResult(
                entry_key=entry_key,
                success=False,
                message=f"Semantic Scholar search failed: {exc}",
            )

        if not resolved_list:
            return ResolveResult(
                entry_key=entry_key,
                success=False,
                message="No candidates found by title search",
            )

        best = None
        best_score = 0.0
        for resolved in resolved_list:
            if not resolved.title:
                continue
            score = title_similarity(title, resolved.title)
            if score > best_score:
                best_score = score
                best = resolved

        if not best or best_score < self.min_confidence:
            return ResolveResult(
                entry_key=entry_key,
                success=False,
                message=f"Low confidence match (best={best_score:.2f} < {self.min_confidence:.2f})",
                confidence=best_score if best else None,
                source="title",
            )

        # Prefer DOI/arXiv if present, otherwise use S2 paper_id
        if best.doi:
            paper_id = f"DOI:{best.doi}"
        elif best.arxiv_id:
            paper_id = f"ARXIV:{best.arxiv_id}"
        else:
            paper_id = best.paper_id

        return ResolveResult(
            entry_key=entry_key,
            success=True,
            message="Resolved by title search",
            paper_id=paper_id,
            source="title",
            confidence=best_score,
        )

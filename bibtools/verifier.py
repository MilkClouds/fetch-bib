"""Core verification logic."""

from __future__ import annotations
from datetime import datetime
from pathlib import Path

from rich.console import Console

from .fetcher import MetadataFetcher
from .models import FieldMismatch, PaperMetadata, VerificationReport, VerificationResult
from .parser import (
    extract_paper_id_from_comments,
    has_missing_date,
    is_entry_verified,
    parse_bib_file,
)
from .semantic_scholar import ResolvedIds
from .utils import compare_authors, compare_titles, compare_venues, title_similarity


def should_skip_verified(date_str: str | None, max_age_days: int | None) -> bool:
    """Determine if a verified entry should be skipped based on age."""
    if max_age_days is None:
        return True
    if max_age_days == 0:
        return False
    if not date_str:
        return False
    try:
        verified_date = datetime.strptime(date_str, "%Y.%m.%d")
        age_days = (datetime.now() - verified_date).days
        return age_days <= max_age_days
    except ValueError:
        return False


def check_field_mismatches(entry: dict, metadata: PaperMetadata) -> tuple[list[FieldMismatch], list[FieldMismatch]]:
    """Check for mismatches between bibtex entry and fetched metadata."""
    source = metadata.source
    mismatches: list[FieldMismatch] = []
    warnings: list[FieldMismatch] = []

    # Title
    bib_title = entry.get("title", "")
    if bib_title and metadata.title:
        match, warning_only = compare_titles(bib_title, metadata.title)
        if not match:
            mismatches.append(
                FieldMismatch(
                    field_name="title",
                    bibtex_value=bib_title,
                    fetched_value=metadata.title,
                    source=source,
                    similarity=title_similarity(bib_title, metadata.title),
                    is_warning=False,
                )
            )
        elif warning_only:
            warnings.append(
                FieldMismatch(
                    field_name="title",
                    bibtex_value=bib_title,
                    fetched_value=metadata.title,
                    source=source,
                    is_warning=True,
                )
            )

    # Authors
    bib_author_field = entry.get("author", "")
    if bib_author_field and metadata.authors:
        from .utils import format_author_bibtex_style

        author_names = [format_author_bibtex_style(a.get("given", ""), a.get("family", "")) for a in metadata.authors]
        api_author_str = metadata.get_authors_str()
        match, warning_only = compare_authors(bib_author_field, author_names)
        if not match:
            mismatches.append(
                FieldMismatch(
                    field_name="author",
                    bibtex_value=bib_author_field,
                    fetched_value=api_author_str,
                    source=source,
                    is_warning=False,
                )
            )
        elif warning_only:
            warnings.append(
                FieldMismatch(
                    field_name="author",
                    bibtex_value=bib_author_field,
                    fetched_value=api_author_str,
                    source=source,
                    is_warning=True,
                )
            )

    # Year
    bib_year = entry.get("year", "")
    if bib_year and metadata.year:
        try:
            bib_year_int = int(bib_year)
            if bib_year_int != metadata.year:
                mismatches.append(
                    FieldMismatch(
                        field_name="year",
                        bibtex_value=str(bib_year_int),
                        fetched_value=str(metadata.year),
                        source=source,
                    )
                )
        except ValueError:
            pass

    # Venue
    bib_venue = entry.get("journal", "") or entry.get("booktitle", "")
    if bib_venue and metadata.venue:
        match, warning_only = compare_venues(bib_venue, metadata.venue)
        if not match:
            mismatches.append(
                FieldMismatch(
                    field_name="venue",
                    bibtex_value=bib_venue,
                    fetched_value=metadata.venue,
                    source=source,
                    is_warning=False,
                )
            )
        elif warning_only:
            warnings.append(
                FieldMismatch(
                    field_name="venue",
                    bibtex_value=bib_venue,
                    fetched_value=metadata.venue,
                    source=source,
                    is_warning=True,
                )
            )

    return mismatches, warnings


def _build_verification_result(
    entry: dict,
    paper_id: str,
    source: str,
    metadata: PaperMetadata,
    mismatches: list[FieldMismatch],
    warnings: list[FieldMismatch],
    *,
    sources: dict[str, PaperMetadata] | None = None,
    arxiv_conflict: bool = False,
) -> VerificationResult:
    entry_key = entry.get("ID", "unknown")

    if mismatches:
        mismatch_fields = ", ".join(m.field_name for m in mismatches)
        return VerificationResult(
            entry_key=entry_key,
            success=False,
            message=f"Field mismatch: {mismatch_fields}",
            metadata=metadata,
            paper_id_used=paper_id,
            paper_id_source=source,
            mismatches=mismatches,
            warnings=warnings,
            sources=sources,
            arxiv_conflict=arxiv_conflict,
        )

    message = "Verified"
    if warnings:
        warning_fields = ", ".join(w.field_name for w in warnings)
        message = f"Verified (warning: {warning_fields} format differs)"

    return VerificationResult(
        entry_key=entry_key,
        success=True,
        message=message,
        metadata=metadata,
        paper_id_used=paper_id,
        paper_id_source=source,
        warnings=warnings,
        mismatches=[],
        fixed=False,
        needs_update=False,
        sources=sources,
        arxiv_conflict=arxiv_conflict,
    )


def _verify_entry_with_resolved(
    entry: dict,
    paper_id: str,
    source: str,
    resolved: ResolvedIds | None,
    *,
    fetcher: MetadataFetcher,
    arxiv_check: bool,
) -> VerificationResult:
    entry_key = entry.get("ID", "unknown")

    if not resolved:
        return VerificationResult(
            entry_key=entry_key,
            success=False,
            message=f"Paper not found for {paper_id}",
            paper_id_used=paper_id,
            paper_id_source=source,
        )

    try:
        bundle = fetcher.fetch_bundle_with_resolved(resolved)
    except Exception as e:
        return VerificationResult(
            entry_key=entry_key,
            success=False,
            message=f"API error: {e}",
            paper_id_used=paper_id,
            paper_id_source=source,
        )

    if not bundle or not bundle.selected:
        return VerificationResult(
            entry_key=entry_key,
            success=False,
            message=f"Paper not found for {paper_id}",
            paper_id_used=paper_id,
            paper_id_source=source,
        )

    metadata = bundle.selected
    if arxiv_check and metadata.source == "arxiv" and not fetcher._is_arxiv_venue(resolved.venue):
        return VerificationResult(
            entry_key=entry_key,
            success=False,
            message=f"Expected venue '{resolved.venue}', but only arXiv metadata was found",
            metadata=metadata,
            paper_id_used=paper_id,
            paper_id_source=source,
            sources=bundle.sources,
        )
    if arxiv_check and bundle.arxiv_conflict:
        return VerificationResult(
            entry_key=entry_key,
            success=False,
            message="source conflict: arXiv differs from selected SoT",
            metadata=metadata,
            paper_id_used=paper_id,
            paper_id_source=source,
            sources=bundle.sources,
            arxiv_conflict=True,
        )

    mismatches, warnings = check_field_mismatches(entry, metadata)
    return _build_verification_result(
        entry,
        paper_id,
        source,
        metadata,
        mismatches,
        warnings,
        sources=bundle.sources,
        arxiv_conflict=bundle.arxiv_conflict,
    )


def verify_entry(
    entry: dict,
    content: str,
    *,
    fetcher: MetadataFetcher,
    skip_verified: bool = True,
    max_age_days: int | None = None,
    arxiv_check: bool = True,
) -> VerificationResult:
    """Verify a single bibtex entry."""
    entry_key = entry.get("ID", "unknown")

    is_verified, date_str, _ = is_entry_verified(content, entry_key)
    if is_verified and skip_verified and should_skip_verified(date_str, max_age_days):
        return VerificationResult(
            entry_key=entry_key,
            success=True,
            message="Already verified",
            already_verified=True,
        )

    paper_id = extract_paper_id_from_comments(content, entry_key)
    if not paper_id:
        return VerificationResult(
            entry_key=entry_key,
            success=True,
            message="No paper_id found",
            no_paper_id=True,
        )

    resolved = fetcher.resolve_batch([paper_id]).get(paper_id)
    return _verify_entry_with_resolved(
        entry,
        paper_id,
        "comment",
        resolved,
        fetcher=fetcher,
        arxiv_check=arxiv_check,
    )


def verify_file(
    file_path: Path,
    *,
    fetcher: MetadataFetcher,
    skip_verified: bool = True,
    max_age_days: int | None = None,
    arxiv_check: bool = True,
    console: Console | None = None,
    show_progress: bool = True,
) -> tuple[VerificationReport, str]:
    """Verify all entries in a bibtex file."""
    from tqdm import tqdm

    console = console or Console()
    entries, content = parse_bib_file(file_path)
    report = VerificationReport()

    entries_to_verify: list[tuple[dict, str, str]] = []
    for entry in entries:
        entry_key = entry.get("ID", "unknown")

        if has_missing_date(content, entry_key):
            report.add_result(
                VerificationResult(
                    entry_key=entry_key,
                    success=False,
                    message="Verification comment missing date. Use format: verified via {verifier} (YYYY.MM.DD)",
                    missing_date=True,
                )
            )
            continue

        is_verified, date_str, _ = is_entry_verified(content, entry_key)
        if is_verified and skip_verified and should_skip_verified(date_str, max_age_days):
            report.add_result(
                VerificationResult(
                    entry_key=entry_key,
                    success=True,
                    message="Already verified",
                    already_verified=True,
                )
            )
            continue

        paper_id = extract_paper_id_from_comments(content, entry_key)
        if not paper_id:
            report.add_result(
                VerificationResult(
                    entry_key=entry_key,
                    success=True,
                    message="No paper_id found",
                    no_paper_id=True,
                )
            )
            continue

        entries_to_verify.append((entry, paper_id, "comment"))

    if not entries_to_verify:
        return report, content

    paper_ids = [paper_id for _, paper_id, _ in entries_to_verify]
    if show_progress:
        console.print(f"[dim]Resolving {len(paper_ids)} paper IDs...[/]")
    resolved_map = fetcher.resolve_batch(paper_ids)

    if show_progress:
        console.print(f"[dim]Verifying {len(entries_to_verify)} entries...[/]")
        entry_iter = tqdm(entries_to_verify, desc="Verifying", unit="entry", leave=False)
    else:
        entry_iter = entries_to_verify

    for entry, paper_id, source in entry_iter:
        resolved = resolved_map.get(paper_id)
        result = _verify_entry_with_resolved(
            entry,
            paper_id,
            source,
            resolved,
            fetcher=fetcher,
            arxiv_check=arxiv_check,
        )
        report.add_result(result)

    return report, content

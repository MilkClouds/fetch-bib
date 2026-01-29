"""CLI interface for bibtools."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from . import __version__
from .fetcher import FetchError, MetadataFetcher
from .models import BibtexEntry
from .parser import extract_paper_id_from_comments, insert_paper_id_comment, parse_bib_file
from .resolver import BibResolver
from .fixer import apply_field_fixes
from .verifier import check_field_mismatches, verify_file

app = typer.Typer(
    name="bibtools",
    help="Bibtex tools: verify, resolve, fetch, and search papers via Semantic Scholar API.",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"bibtools version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Bibtools - Bibtex utilities powered by Semantic Scholar."""


@app.command()
def verify(
    bib_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the .bib file to verify.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    skip_verified: Annotated[
        bool,
        typer.Option(
            "--skip-verified/--reverify",
            help="Skip entries that are already verified. --reverify is equivalent to --max-age=0.",
        ),
    ] = True,
    max_age: Annotated[
        int | None,
        typer.Option(
            "--max-age",
            help="Re-verify entries older than this many days. Overrides --skip-verified.",
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar="SEMANTIC_SCHOLAR_API_KEY",
            help="Semantic Scholar API key for higher rate limits.",
        ),
    ] = None,
    arxiv_check: Annotated[
        bool,
        typer.Option(
            "--arxiv-check/--no-arxiv-check",
            help="Cross-check with arXiv when arXiv ID exists. Detects wrong papers from DBLP/CrossRef.",
        ),
    ] = True,
) -> None:
    """Verify bibtex entries using Semantic Scholar API.

    Examples:
      bibtools verify main.bib
      bibtools verify main.bib --reverify
    """
    # Display settings
    console.print(f"\n[bold blue]Verifying:[/] {bib_file}")

    if not arxiv_check:
        console.print("[dim]arXiv cross-check:[/] disabled")

    # Handle --reverify as --max-age=0
    effective_max_age = max_age
    if not skip_verified:
        effective_max_age = 0  # --reverify = --max-age 0

    if effective_max_age is not None:
        if effective_max_age == 0:
            console.print("[dim]Re-verify:[/] all entries (--reverify or --max-age=0)")
        else:
            console.print(f"[dim]Re-verify:[/] entries older than {effective_max_age} days")

    fetcher = MetadataFetcher(api_key=api_key)
    try:
        report, _ = verify_file(
            bib_file,
            fetcher=fetcher,
            skip_verified=True,
            max_age_days=effective_max_age,
            arxiv_check=arxiv_check,
            console=console,
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        fetcher.close()

    # Print results (always show important info)
    _print_actionable_results(report)
    _print_summary(report)

    # Exit with appropriate code based on overall status
    # 0=PASS, 1=WARNING, 2=FAIL
    raise typer.Exit(report.exit_code)


@app.command()
def resolve(
    bib_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the .bib file to resolve paper_id comments for.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path. If not specified, modifies the input file in-place.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Don't modify files, just show what would be done.",
        ),
    ] = False,
    min_confidence: Annotated[
        float,
        typer.Option(
            "--min-confidence",
            help="Minimum title-match confidence for auto-resolution.",
        ),
    ] = 0.85,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar="SEMANTIC_SCHOLAR_API_KEY",
            help="Semantic Scholar API key for higher rate limits.",
        ),
    ] = None,
) -> None:
    """Resolve paper_id comments for bibtex entries (no verification)."""
    console.print(f"\n[bold blue]Resolving:[/] {bib_file}")
    console.print(f"[dim]Min confidence:[/] {min_confidence:.2f}")

    resolver = BibResolver(api_key=api_key, min_confidence=min_confidence, console=console)
    try:
        report, updated_content = resolver.resolve_file(bib_file)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        resolver.close()

    _print_resolve_results(report)

    if not dry_run and report.resolved > 0:
        output_path = output or bib_file
        output_path.write_text(updated_content, encoding="utf-8")
        console.print(f"\n[bold green]Updated:[/] {output_path}")
    elif dry_run:
        console.print("\n[yellow]Dry run - no files modified.[/]")


@app.command()
def review(
    bib_file: Annotated[
        Path,
        typer.Argument(
            help="Path to the .bib file to review and fix interactively.",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output file path. If not specified, modifies the input file in-place.",
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar="SEMANTIC_SCHOLAR_API_KEY",
            help="Semantic Scholar API key for higher rate limits.",
        ),
    ] = None,
    arxiv_check: Annotated[
        bool,
        typer.Option(
            "--arxiv-check/--no-arxiv-check",
            help="Cross-check with arXiv when arXiv ID exists. Detects wrong papers from DBLP/CrossRef.",
        ),
    ] = True,
    allow_warning: Annotated[
        bool,
        typer.Option(
            "--allow-warning/--no-allow-warning",
            help="When false (default), WARNING entries are reviewed. When true, warnings are auto-accepted.",
        ),
    ] = False,
    verified_via: Annotated[
        str | None,
        typer.Option(
            "--verified-via",
            help="Verifier name to record in the comment (e.g., 'human(Alice)').",
        ),
    ] = None,
) -> None:
    """Interactively review and fix mismatched bibtex entries."""
    console.print(f"\n[bold blue]Reviewing:[/] {bib_file}")
    review_warnings = not allow_warning

    fetcher = MetadataFetcher(api_key=api_key)
    try:
        report, content = verify_file(
            bib_file,
            fetcher=fetcher,
            skip_verified=True,
            max_age_days=None,
            arxiv_check=arxiv_check,
            console=console,
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        fetcher.close()

    entries, _ = parse_bib_file(bib_file)
    entry_map = {entry.get("ID", ""): entry for entry in entries}

    updated_content = content
    verifier_name = verified_via
    if not verifier_name:
        verifier_name = typer.prompt("What's your name?")
    applied = 0

    for result in report.results:
        if result.no_paper_id:
            console.print(f"[yellow]No paper_id:[/] {result.entry_key} (run `bibtools resolve` first)")
            continue
        if result.already_verified:
            continue
        if result.missing_date:
            console.print(f"[red]Missing date:[/] {result.entry_key} ({result.message})")
            continue
        if not result.success and not result.mismatches and not result.warnings and not result.arxiv_conflict:
            console.print(f"[red]Error:[/] {result.entry_key} ({result.message})")
            continue

        if result.success and not result.mismatches and not result.warnings and not result.arxiv_conflict:
            paper_id = extract_paper_id_from_comments(updated_content, result.entry_key) or result.paper_id_used
            if paper_id and result.metadata:
                verifier_tag = f"{verifier_name}[source={result.metadata.source or 'unknown'}]"
                updated_content = insert_paper_id_comment(
                    updated_content,
                    result.entry_key,
                    paper_id,
                    include_verified=True,
                    verifier_name=verifier_tag,
                )
                console.print(f"[green]Verified:[/] {result.entry_key} (no mismatches)")
                applied += 1
            else:
                console.print(f"[yellow]Missing paper_id comment for {result.entry_key}; cannot mark verified.[/]")
            continue

        if result.mismatches:
            pass
        elif result.arxiv_conflict:
            pass
        elif review_warnings and result.warnings:
            pass
        else:
            continue

        entry = entry_map.get(result.entry_key)
        if not entry or not result.metadata:
            console.print(f"[yellow]Skipping {result.entry_key} (missing metadata).[/]")
            continue

        console.print(f"\n[bold cyan]{result.entry_key}[/]")
        meta = result.metadata
        selected_source = meta.source or "unknown"
        selected_meta = meta
        chose_source = False

        if result.arxiv_conflict and result.sources and "arxiv" in result.sources:
            arxiv_pm = result.sources["arxiv"]

            console.print("[yellow]Source conflict detected (arXiv vs official source).[/]")
            console.print(f"[dim]1) {meta.source}[/] vs [dim]2) arXiv[/]")

            def _norm_text(value: str | None) -> str:
                return " ".join((value or "").split()).strip()

            def _format_authors(pm, max_authors=8):
                names = [f"{a.get('given', '').strip()} {a.get('family', '').strip()}".strip() for a in pm.authors]
                names = [n for n in names if n]
                if not names:
                    return "N/A"
                if len(names) > max_authors:
                    return ", ".join(names[:max_authors]) + f" (+{len(names) - max_authors} more)"
                return ", ".join(names)

            meta_title = _norm_text(meta.title)
            arxiv_title = _norm_text(arxiv_pm.title)
            if meta_title != arxiv_title:
                console.print(f"[dim]  title 1:[/] {meta_title or 'N/A'}")
                console.print(f"[dim]  title 2:[/] {arxiv_title or 'N/A'}")

            if (meta.year or "N/A") != (arxiv_pm.year or "N/A"):
                console.print(f"[dim]   year 1:[/] {meta.year or 'N/A'}")
                console.print(f"[dim]   year 2:[/] {arxiv_pm.year or 'N/A'}")

            if _norm_text(meta.venue) != _norm_text(arxiv_pm.venue):
                console.print(f"[dim]  venue 1:[/] {meta.venue or 'N/A'}")
                console.print(f"[dim]  venue 2:[/] {arxiv_pm.venue or 'N/A'}")

            if _format_authors(meta) != _format_authors(arxiv_pm):
                console.print(f"[dim] authors 1:[/] {_format_authors(meta)}")
                console.print(f"[dim] authors 2:[/] {_format_authors(arxiv_pm)}")

            choice = typer.prompt("Choose source of truth (1/2/skip)", default="skip", show_default=True)
            normalized = choice.strip().lower()
            if normalized == "2":
                selected_meta = arxiv_pm
                selected_source = "arxiv"
                chose_source = True
            elif normalized in {"skip", "s"}:
                continue
            else:
                selected_meta = meta
                selected_source = meta.source or "unknown"
                chose_source = True

            result.mismatches, result.warnings = check_field_mismatches(entry, selected_meta)

        console.print(f"[dim]Source:[/] {selected_source} | [dim]Venue:[/] {selected_meta.venue or 'N/A'}")
        if result.mismatches:
            console.print("[red]Mismatches:[/]")
            for mismatch in result.mismatches:
                console.print(f"  [red]{mismatch.field_name}[/]")
                console.print(f"    {'yours:':>10} {' '.join(mismatch.bibtex_value.split())}")
                source_label = f"{mismatch.source}:"
                console.print(f"    {source_label:>10} {' '.join(mismatch.fetched_value.split())}")

        if review_warnings and result.warnings:
            console.print("[yellow]Warnings:[/]")
            for warning in result.warnings:
                console.print(f"  [yellow]{warning.field_name}[/]")
                console.print(f"    {'yours:':>10} {' '.join(warning.bibtex_value.split())}")
                source_label = f"{warning.source}:"
                console.print(f"    {source_label:>10} {' '.join(warning.fetched_value.split())}")

        apply_default = True if chose_source else False
        wants_apply = typer.confirm("Apply changes for this entry?", default=apply_default)
        if not wants_apply:
            if result.warnings and not result.mismatches and review_warnings:
                paper_id = extract_paper_id_from_comments(updated_content, result.entry_key) or result.paper_id_used
                if paper_id and typer.confirm("Mark verified via for warnings?", default=False):
                    verifier_tag = f"{verifier_name}[source={selected_source}]"
                    updated_content = insert_paper_id_comment(
                        updated_content,
                        result.entry_key,
                        paper_id,
                        include_verified=True,
                        verifier_name=verifier_tag,
                    )
                    console.print(f"[green]Verified:[/] {result.entry_key} (warnings only)")
                    applied += 1
            continue

        selected = []
        for mismatch in result.mismatches:
            if typer.confirm(f"  Replace {mismatch.field_name}?", default=True):
                selected.append(mismatch)

        if review_warnings:
            for warning in result.warnings:
                if typer.confirm(f"  Replace {warning.field_name} (warning)?", default=True):
                    selected.append(warning)

        if not selected:
            if result.warnings and not result.mismatches and review_warnings:
                paper_id = extract_paper_id_from_comments(updated_content, result.entry_key) or result.paper_id_used
                if paper_id and typer.confirm("Mark verified via for warnings?", default=wants_apply):
                    verifier_tag = f"{verifier_name}[source={selected_source}]"
                    updated_content = insert_paper_id_comment(
                        updated_content,
                        result.entry_key,
                        paper_id,
                        include_verified=True,
                        verifier_name=verifier_tag,
                    )
                    console.print(f"[green]Verified:[/] {result.entry_key} (warnings only)")
                    applied += 1
                else:
                    console.print("[yellow]No fields selected; skipping.[/]")
            else:
                console.print("[yellow]No fields selected; skipping.[/]")
            continue

        updated_content = apply_field_fixes(updated_content, entry, selected_meta, selected)
        paper_id = extract_paper_id_from_comments(updated_content, result.entry_key) or result.paper_id_used
        has_mismatch_selected = any(item in selected for item in result.mismatches)
        has_warning_selected = any(item in selected for item in result.warnings)
        if paper_id:
            if has_warning_selected and not has_mismatch_selected:
                if not typer.confirm("Mark verified via for warnings?", default=wants_apply):
                    applied += 1
                    continue
            verifier_tag = f"{verifier_name}[source={selected_source}]"
            updated_content = insert_paper_id_comment(
                updated_content,
                result.entry_key,
                paper_id,
                include_verified=True,
                verifier_name=verifier_tag,
            )
        else:
            console.print(
                f"[yellow]No paper_id available for {result.entry_key} (missing comment and resolved id); "
                "cannot mark verified.[/]"
            )
        applied += 1

    if applied == 0:
        console.print("\n[dim]No changes applied.[/]")
        return

    output_path = output or bib_file
    output_path.write_text(updated_content, encoding="utf-8")
    console.print(f"\n[bold green]Updated:[/] {output_path}")


@app.command()
def fetch(
    paper_id: Annotated[
        str,
        typer.Argument(
            help="Paper ID: ARXIV:id, DOI:doi, CorpusId:id, ACL:id, PMID:id, etc.",
        ),
    ],
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar="SEMANTIC_SCHOLAR_API_KEY",
            help="Semantic Scholar API key for higher rate limits.",
        ),
    ] = None,
) -> None:
    """Fetch bibtex entry by paper ID.

    Examples:
        bibtools fetch ARXIV:2106.15928
        bibtools fetch "DOI:10.18653/v1/N18-3011"
    """
    fetcher = MetadataFetcher(api_key=api_key)
    try:
        bundle = fetcher.fetch_bundle(paper_id)
    except FetchError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)
    finally:
        fetcher.close()

    if not bundle or not bundle.selected:
        console.print(f"[bold red]Error:[/] Paper not found: {paper_id}")
        raise typer.Exit(1)

    meta = bundle.selected
    bibtex = BibtexEntry.from_metadata(meta).to_bibtex(paper_id)
    authors_str = ", ".join(f"{a['given']} {a['family']}" for a in meta.authors[:3])
    if len(meta.authors) > 3:
        authors_str += f" et al. ({len(meta.authors)} authors)"

    console.print(f"\n[bold green]Found:[/] {meta.title}")
    console.print(f"[dim]Source:[/] {meta.source} | [dim]Year:[/] {meta.year}")
    console.print(f"[dim]Venue:[/] {meta.venue or 'N/A'}")
    console.print(f"[dim]Authors:[/] {authors_str}")
    console.print()
    console.print(bibtex)


@app.command()
def search(
    query: Annotated[
        str,
        typer.Argument(
            help="Search query: paper title or keywords.",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of results.",
        ),
    ] = 5,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            "-k",
            envvar="SEMANTIC_SCHOLAR_API_KEY",
            help="Semantic Scholar API key for higher rate limits.",
        ),
    ] = None,
) -> None:
    """Search papers by title/keywords and generate bibtex.

    ⚠️  WARNING: Search results may not match your intended paper.
    Always verify the returned bibtex before using.

    Examples:
        bibtools search "Attention Is All You Need"
        bibtools search "diffusion policy robot" --limit 3
    """
    console.print(
        "\n[bold yellow]⚠️  WARNING:[/] Search results may not match your intended paper.\n"
        "   Always verify the returned bibtex before using.\n"
    )

    fetcher = MetadataFetcher(api_key=api_key)
    try:
        resolved_list = fetcher.s2_client.search_by_title(query, limit=limit)
        results: list[tuple[str, object]] = []
        for resolved in resolved_list:
            bundle = fetcher.fetch_bundle_with_resolved(resolved)
            if bundle and bundle.selected:
                metadata = bundle.selected
                bibtex = BibtexEntry.from_metadata(metadata).to_bibtex(resolved.paper_id)
                results.append((bibtex, metadata))
    finally:
        fetcher.close()

    if not results:
        console.print(f"[bold red]No results found for:[/] {query}")
        raise typer.Exit(1)

    console.print(f"[bold blue]Found {len(results)} result(s) for:[/] {query}\n")

    for i, (bibtex, metadata) in enumerate(results, 1):
        venue = metadata.venue or "N/A"
        console.print(f"[bold cyan]#{i}[/] {metadata.title} ({metadata.year}, {venue})\n")
        console.print(bibtex)
        console.print()


def _print_actionable_results(report) -> None:
    """Print all actionable results (failures, warnings)."""
    # 1. Failures (field mismatches)
    failed_with_mismatches = [r for r in report.results if r.mismatches and not r.success and not r.fixed]
    if failed_with_mismatches:
        console.print("\n[bold red]✗ Field Mismatches:[/]")
        for result in failed_with_mismatches:
            console.print(f"\n  [cyan]{result.entry_key}[/]:")
            for mismatch in result.mismatches:
                sim_str = f" (similarity: {mismatch.similarity:.0%})" if mismatch.similarity else ""
                console.print(f"    [red]{mismatch.field_name}[/]{sim_str}")
                console.print(f"    {'yours:':>10} {' '.join(mismatch.bibtex_value.split())}")
                source_label = f"{mismatch.source}:"
                console.print(f"    {source_label:>10} {' '.join(mismatch.fetched_value.split())}")

    # 2. Missing date errors (verified via without date)
    missing_date_errors = [r for r in report.results if r.missing_date]
    if missing_date_errors:
        console.print("\n[bold red]✗ Missing date (required format: verified via {verifier} (YYYY.MM.DD)):[/]")
        for result in missing_date_errors:
            console.print(f"  [cyan]{result.entry_key}[/]: {result.message}")

    # 3. Other failures (paper not found, API errors)
    other_failures = [
        r
        for r in report.results
        if not r.success and not r.mismatches and not r.no_paper_id and not r.already_verified and not r.missing_date
    ]
    if other_failures:
        console.print("\n[bold red]✗ Errors:[/]")
        for result in other_failures:
            console.print(f"  [cyan]{result.entry_key}[/]: {result.message}")

    # 3. Warnings (no paper_id)
    no_paper_id = [r for r in report.results if r.no_paper_id]
    if no_paper_id:
        console.print("\n[bold yellow]⚠ No paper_id (add doi/eprint or verification comment):[/]")
        for result in no_paper_id:
            console.print(f"  [cyan]{result.entry_key}[/]")

    # 4. Warnings from successful entries (e.g., LaTeX braces, case differences)
    entries_with_warnings = [r for r in report.results if r.warnings and r.success]
    if entries_with_warnings:
        console.print("\n[bold yellow]⚠ Warnings (format differs - verified but check):[/]")
        for result in entries_with_warnings:
            console.print(f"\n  [cyan]{result.entry_key}[/]:")
            for warning in result.warnings:
                console.print(f"    [yellow]{warning.field_name}[/]")
                console.print(f"    {'yours:':>10} {' '.join(warning.bibtex_value.split())}")
                source_label = f"{warning.source}:"
                console.print(f"    {source_label:>10} {' '.join(warning.fetched_value.split())}")

    # No auto-fix or auto-annotation in verify.


def _print_summary(report) -> None:
    """Print summary statistics."""
    from .models import VerificationStatus

    console.print("\n[bold]Summary:[/]")
    console.print(f"  Total entries: {report.total_entries}")
    console.print(f"  [green]Verified (pass): {report.verified}[/]")
    if report.verified_with_warnings > 0:
        console.print(f"  [yellow]Verified (warning): {report.verified_with_warnings}[/]")
    console.print(f"  [dim]Already verified: {report.already_verified}[/]")
    if report.no_paper_id > 0:
        console.print(f"  [yellow]No paper_id: {report.no_paper_id}[/]")
    if report.missing_date > 0:
        console.print(f"  [red]Missing date: {report.missing_date}[/]")
    if report.failed > 0:
        console.print(f"  [red]Failed: {report.failed}[/]")

    # Show overall status
    status = report.overall_status
    if status == VerificationStatus.PASS:
        console.print("\n[bold green]Result: PASS[/] (exit code 0)")
    elif status == VerificationStatus.WARNING:
        console.print("\n[bold yellow]Result: WARNING[/] (exit code 1)")
    else:
        console.print("\n[bold red]Result: FAIL[/] (exit code 2)")


def _print_resolve_results(report) -> None:
    """Print resolve report details."""
    if report.resolved == 0 and report.failed == 0:
        console.print("\n[dim]No entries to resolve.[/]")
        return

    resolved = [r for r in report.results if r.success and not r.already_has_paper_id]
    if resolved:
        console.print("\n[bold green]✓ Resolved:[/]")
        for result in resolved:
            conf = f"{result.confidence:.2f}" if result.confidence is not None else "n/a"
            console.print(
                f"  [cyan]{result.entry_key}[/]: {result.paper_id} "
                f"[dim](source: {result.source}, confidence: {conf})[/]"
            )

    failed = [r for r in report.results if not r.success]
    if failed:
        console.print("\n[bold red]✗ Unresolved:[/]")
        for result in failed:
            console.print(f"  [cyan]{result.entry_key}[/]: {result.message}")

    skipped = [r for r in report.results if r.already_has_paper_id]
    if skipped:
        console.print("\n[dim]Skipped (already has paper_id):[/]")
        for result in skipped:
            console.print(f"  [cyan]{result.entry_key}[/]: {result.paper_id}")


if __name__ == "__main__":
    app()

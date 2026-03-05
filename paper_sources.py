#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx",
#     "rich",
#     "python-dotenv",
# ]
# ///
"""Fetch paper metadata from multiple sources and present side-by-side.

This tool fetches and presents. It never judges.

Each source returns what it has — no filtering, no "best source" selection,
no hardcoded venue maps. The human (or AI agent downstream) decides what to trust.

Sources: Semantic Scholar (ID resolution), CrossRef, DBLP, arXiv, OpenReview, ACL Anthology.

Usage:
    uv run paper_sources.py 2010.11929            # arXiv ID (ViT)
    uv run paper_sources.py 1706.03762            # arXiv ID (Attention)
    uv run paper_sources.py 10.18653/v1/N19-1423  # DOI (BERT)
    uv run paper_sources.py --json 2010.11929     # JSON output for piping
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

# =============================================================================
# Models
# =============================================================================


@dataclass
class SourceResult:
    """Metadata returned by a single source."""

    source: str
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    entry_type: str | None = None
    doi: str | None = None
    url: str | None = None
    pages: str | None = None
    volume: str | None = None
    number: str | None = None
    bibtex: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ResolvedPaper:
    """IDs resolved via Semantic Scholar."""

    paper_id: str
    doi: str | None = None
    arxiv_id: str | None = None
    dblp_id: str | None = None
    acl_id: str | None = None
    venue: str | None = None
    title: str | None = None


# =============================================================================
# Helpers
# =============================================================================


def _normalize_paper_id(paper_id: str) -> str:
    """Add ARXIV: prefix to bare arXiv IDs."""
    if ":" in paper_id or "/" in paper_id:
        return paper_id
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", paper_id):
        return f"ARXIV:{paper_id}"
    return paper_id


def _titles_match(t1: str, t2: str) -> bool:
    """Fuzzy title match: ignore punctuation and case."""

    def norm(t: str) -> str:
        return " ".join(re.sub(r"[^\w\s]", " ", t.lower()).split())

    return norm(t1) == norm(t2)


def _request(client: httpx.Client, url: str, *, headers: dict | None = None, **kwargs: Any) -> httpx.Response | None:
    """GET with retry on 429. Returns None on 404."""
    hdrs = headers or {}
    for attempt in range(3):
        resp = client.get(url, headers=hdrs, **kwargs)
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            wait = (attempt + 1) * 5
            print(f"  Rate limited ({url[:60]}…), retrying in {wait}s…", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    return None


# =============================================================================
# Source: Semantic Scholar (ID resolution only)
# =============================================================================

_S2_BASE = "https://api.semanticscholar.org/graph/v1"
_S2_FIELDS = "paperId,externalIds,venue,title"


def _s2_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if key:
        headers["x-api-key"] = key
    return headers


def resolve_s2(client: httpx.Client, paper_id: str) -> ResolvedPaper | None:
    normalized = _normalize_paper_id(paper_id)
    try:
        resp = _request(client, f"{_S2_BASE}/paper/{normalized}", headers=_s2_headers(), params={"fields": _S2_FIELDS})
    except httpx.HTTPError as e:
        print(f"  S2 error: {e}", file=sys.stderr)
        return None
    if not resp:
        return None

    data = resp.json()
    pid = data.get("paperId", "")
    if not pid:
        return None

    ext = data.get("externalIds") or {}
    doi = ext.get("DOI")

    return ResolvedPaper(
        paper_id=pid,
        doi=doi,
        arxiv_id=ext.get("ArXiv"),
        dblp_id=ext.get("DBLP"),
        acl_id=ext.get("ACL"),
        venue=data.get("venue") or None,
        title=data.get("title") or None,
    )


# =============================================================================
# Source: CrossRef
# =============================================================================


def fetch_crossref(client: httpx.Client, doi: str) -> SourceResult | None:
    doi = doi.removeprefix("DOI:").removeprefix("doi:")
    try:
        resp = _request(
            client,
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "paper_sources/0.1 (https://github.com/bibtools)"},
        )
    except httpx.HTTPError as e:
        return SourceResult(source="crossref", error=str(e))
    if not resp:
        return None

    msg = resp.json().get("message", {})

    # Title (may contain HTML entities/tags)
    raw_title = (msg.get("title") or [""])[0]
    title = html_mod.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip() or None

    authors = [f"{a.get('given', '')} {a['family']}".strip() for a in msg.get("author", []) if "family" in a]

    year = None
    for key in ("published", "issued"):
        parts = msg.get(key, {}).get("date-parts", [[]])
        if parts and parts[0]:
            year = parts[0][0]
            break

    return SourceResult(
        source="crossref",
        title=title,
        authors=authors,
        year=year,
        venue=(msg.get("container-title") or [None])[0],
        doi=doi,
        pages=msg.get("page"),
        volume=msg.get("volume"),
        number=msg.get("issue"),
    )


# =============================================================================
# Source: DBLP
# =============================================================================


def fetch_dblp(client: httpx.Client, title: str, venue: str | None = None) -> SourceResult | None:
    if not title:
        return None

    # Try with venue first (if available), then title-only as fallback
    queries = [f"{title} {venue}", title] if venue else [title]
    for query in queries:
        try:
            resp = client.get("https://dblp.org/search/publ/api", params={"q": query, "format": "json", "h": 10})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            return SourceResult(source="dblp", error=str(e))

        for hit in resp.json().get("result", {}).get("hits", {}).get("hit", []):
            info = hit.get("info", {})
            key = info.get("key", "")
            hit_title = (info.get("title") or "").rstrip(".")
            if _titles_match(title, hit_title):
                return _parse_dblp_hit(info, key)

    return None


def _parse_dblp_hit(info: dict, key: str) -> SourceResult:
    authors_raw = info.get("authors", {}).get("author", [])
    if isinstance(authors_raw, dict):
        authors_raw = [authors_raw]
    authors = []
    for a in authors_raw:
        name = a.get("text", "") if isinstance(a, dict) else str(a)
        name = re.sub(r"\s+\d{4}$", "", name)  # Remove trailing disambiguation year
        if name:
            authors.append(name)

    year_s = info.get("year", "")
    return SourceResult(
        source="dblp",
        title=(info.get("title") or "").rstrip("."),
        authors=authors,
        year=int(year_s) if year_s else None,
        venue=info.get("venue", ""),
        doi=info.get("doi"),
        entry_type=info.get("type", ""),
        extra={"dblp_key": key},
    )


# =============================================================================
# Source: arXiv (Atom API — no extra dependency)
# =============================================================================

_ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_arxiv(client: httpx.Client, arxiv_id: str) -> SourceResult | None:
    arxiv_id = arxiv_id.upper().removeprefix("ARXIV:").lower()
    if "v" in arxiv_id:
        arxiv_id = arxiv_id.rsplit("v", 1)[0]

    try:
        resp = client.get("https://export.arxiv.org/api/query", params={"id_list": arxiv_id, "max_results": 1})
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return SourceResult(source="arxiv", error=str(e))

    root = ET.fromstring(resp.text)
    entry = root.find("atom:entry", _ARXIV_NS)
    if entry is None:
        return None

    entry_id = entry.findtext("atom:id", "", _ARXIV_NS)
    if "error" in entry_id.lower():
        return None

    title = " ".join((entry.findtext("atom:title", "", _ARXIV_NS) or "").split())
    authors = [
        name
        for el in entry.findall("atom:author", _ARXIV_NS)
        if (name := (el.findtext("atom:name", "", _ARXIV_NS) or "").strip())
    ]
    published = entry.findtext("atom:published", "", _ARXIV_NS) or ""
    year = int(published[:4]) if len(published) >= 4 else None

    categories = []
    for tag in ("arxiv:primary_category", "atom:category"):
        for el in entry.findall(tag, _ARXIV_NS):
            if (term := el.get("term")) and term not in categories:
                categories.append(term)

    return SourceResult(
        source="arxiv",
        title=title,
        authors=authors,
        year=year,
        extra={"arxiv_id": arxiv_id, "categories": categories},
    )


# =============================================================================
# Source: OpenReview (v1 search + v2 fallback)
# =============================================================================


def _or_val(content: dict, key: str) -> Any:
    """Extract value from OpenReview content field (handles both v1 plain and v2 {value: …} wrapper)."""
    v = content.get(key)
    return v.get("value") if isinstance(v, dict) else v


def fetch_openreview(client: httpx.Client, title: str) -> SourceResult | None:
    if not title:
        return None

    # Try v1 first (better coverage for older papers), then v2
    for base in ("https://api.openreview.net", "https://api2.openreview.net"):
        try:
            resp = client.get(f"{base}/notes/search", params={"query": title, "limit": 5, "source": "forum"})
            resp.raise_for_status()
        except httpx.HTTPError:
            continue

        for note in resp.json().get("notes", []):
            note_title = _or_val(note.get("content", {}), "title")
            if note_title and _titles_match(title, note_title):
                return _parse_openreview_note(note)

    return None


def _parse_openreview_note(note: dict) -> SourceResult:
    content = note.get("content", {})
    authors = _or_val(content, "authors") or []
    if isinstance(authors, str):
        authors = [authors]
    venue = _or_val(content, "venue") or _or_val(content, "venueid") or ""

    # Extract year from venue or invitation string
    inv = (note.get("invitations") or [note.get("invitation", "")])[0] or ""
    m = re.search(r"20\d{2}", f"{venue} {inv}")

    return SourceResult(
        source="openreview",
        title=_or_val(content, "title") or "",
        authors=authors,
        year=int(m.group()) if m else None,
        venue=venue,
        url=f"https://openreview.net/forum?id={note.get('id', '')}",
    )


# =============================================================================
# Source: ACL Anthology
# =============================================================================


def fetch_acl(client: httpx.Client, acl_id: str) -> SourceResult | None:
    if not acl_id:
        return None
    try:
        resp = client.get(f"https://aclanthology.org/{acl_id}.bib", follow_redirects=True)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return SourceResult(source="acl_anthology", error=str(e))
    return _parse_bibtex_str(resp.text.strip(), source="acl_anthology")


def _parse_bibtex_str(bibtex: str, *, source: str) -> SourceResult:
    """Regex-based BibTeX parser (good enough for single well-formed entries)."""

    def extract(fld: str) -> str | None:
        m = re.search(rf'{fld}\s*=\s*"([^"]*)"', bibtex)
        if not m:
            m = re.search(rf"{fld}\s*=\s*\{{([^}}]*)\}}", bibtex)
        return m.group(1).strip() if m else None

    author_str = extract("author")
    authors = [x.strip() for x in re.split(r"\s+and\s+", author_str) if x.strip()] if author_str else []
    year_str = extract("year")
    type_m = re.match(r"@(\w+)\{", bibtex)

    return SourceResult(
        source=source,
        bibtex=bibtex,
        title=extract("title"),
        authors=authors,
        year=int(year_str) if year_str else None,
        venue=extract("booktitle") or extract("journal"),
        pages=extract("pages"),
        volume=extract("volume"),
        doi=extract("doi"),
        url=extract("url"),
        entry_type=type_m.group(1) if type_m else None,
    )


# =============================================================================
# Orchestrator
# =============================================================================

# (source_key, fetch_function, condition_field)
# condition_field: which ResolvedPaper attr must be truthy to attempt this source.
_SOURCES: list[tuple[str, Any, str]] = [
    ("crossref", fetch_crossref, "doi"),
    ("dblp", fetch_dblp, "title"),
    ("arxiv", fetch_arxiv, "arxiv_id"),
    ("openreview", fetch_openreview, "title"),
    ("acl_anthology", fetch_acl, "acl_id"),
]

ALL_SOURCES = [name for name, _, _ in _SOURCES]


def fetch_all(paper_id: str, log: Console, *, sources: list[str] | None = None) -> dict[str, SourceResult]:
    """Resolve paper ID, then fetch metadata from selected sources.

    Args:
        sources: Which sources to fetch from. None means all.
    """
    enabled = sources or ALL_SOURCES
    results: dict[str, SourceResult] = {}

    with httpx.Client(timeout=30.0) as client:
        # Step 1: Resolve IDs via Semantic Scholar
        log.print(f"[dim]Resolving {paper_id} via Semantic Scholar…[/]")
        resolved = resolve_s2(client, paper_id)
        if not resolved:
            log.print(f"[red]Paper not found: {paper_id}[/]")
            return results

        log.print(
            f"[dim]  DOI: {resolved.doi or '—'}  arXiv: {resolved.arxiv_id or '—'}  "
            f"venue: {resolved.venue or '—'}  ACL: {resolved.acl_id or '—'}[/]"
        )
        log.print(f"[dim]  title: {(resolved.title or '—')[:80]}[/]")
        log.print()

        results["semantic_scholar"] = SourceResult(
            source="semantic_scholar",
            title=resolved.title,
            venue=resolved.venue,
            doi=resolved.doi,
            extra={"arxiv_id": resolved.arxiv_id, "dblp_id": resolved.dblp_id, "acl_id": resolved.acl_id},
        )

        # Step 2: Fetch from each enabled source
        for name, fetch_fn, cond_field in _SOURCES:
            if name not in enabled:
                log.print(f"  [dim]{name}: skipped (disabled)[/]")
                continue
            arg = getattr(resolved, cond_field, None)
            if not arg:
                log.print(f"  [dim]{name}: skipped (no {cond_field})[/]")
                continue
            log.print(f"  [dim]{name}: fetching…[/]", end="")
            if name == "dblp":
                result = fetch_fn(client, resolved.title, resolved.venue)
            else:
                result = fetch_fn(client, arg)
            if result and result.error:
                log.print(f" [red]error: {result.error}[/]")
                results[name] = result
            elif result:
                log.print(" [green]ok[/]")
                results[name] = result
            else:
                log.print(" [yellow]no match[/]")

    return results


# =============================================================================
# Display: Rich table
# =============================================================================

_DISPLAY_FIELDS = ["title", "authors", "year", "venue", "entry_type", "doi", "pages", "volume"]


def _format_cell(result: SourceResult, field_name: str) -> str:
    """Format a single cell value for the comparison table."""
    if result.error:
        return "[dim]—[/]"
    val = getattr(result, field_name, None)
    if val is None:
        return "[dim]—[/]"
    if field_name == "authors" and isinstance(val, list):
        display = ", ".join(val[:3])
        if len(val) > 3:
            display += f" (+{len(val) - 3})"
        return display
    return str(val)


def _compute_diffs(results: dict[str, SourceResult], sources: list[str]) -> list[str]:
    """Compute field-level diffs between sources."""
    diffs: list[str] = []

    # Year + venue diffs
    for f in ("year", "venue"):
        vals = {}
        for src in sources:
            r = results[src]
            v = getattr(r, f, None) if not r.error else None
            if v is not None:
                vals[src] = str(v)[:50]
        if len(set(vals.values())) > 1:
            diffs.append(f"  [yellow]{f}[/]: " + ", ".join(f"{s}={v}" for s, v in vals.items()))

    # Title diff (ignore LaTeX braces)
    title_vals = {src: results[src].title for src in sources if not results[src].error and results[src].title}
    normalized = {s: re.sub(r"[{}]", "", t).strip() for s, t in title_vals.items() if t}
    if len(set(normalized.values())) > 1:
        diffs.append("  [yellow]title[/]: " + ", ".join(f"{s}={v[:50]}" for s, v in title_vals.items() if v))

    # Author count diff
    acounts = {src: len(results[src].authors) for src in sources if not results[src].error and results[src].authors}
    if len(set(acounts.values())) > 1:
        diffs.append("  [yellow]author_count[/]: " + ", ".join(f"{s}={n}" for s, n in acounts.items()))

    return diffs


def display_rich(results: dict[str, SourceResult], console: Console) -> None:
    # Header: pick best title
    title = next(
        (results[s].title for s in (*ALL_SOURCES, "semantic_scholar") if s in results and results[s].title), None
    )
    s2 = results.get("semantic_scholar")

    console.print()
    console.rule(f"[bold]{title or 'Unknown'}[/bold]")
    if s2:
        parts = []
        if s2.extra.get("arxiv_id"):
            parts.append(f"arXiv: {s2.extra['arxiv_id']}")
        if s2.doi:
            parts.append(f"DOI: {s2.doi}")
        if s2.venue:
            parts.append(f"S2 venue: {s2.venue}")
        if parts:
            console.print(f"  [dim]{' │ '.join(parts)}[/]")
    console.print()

    # Comparison table
    sources = [s for s in ALL_SOURCES if s in results]
    if not sources:
        console.print("[yellow]No metadata sources returned results.[/]")
        return

    table = Table(show_header=True, header_style="bold", expand=True, show_lines=True)
    table.add_column("Field", style="cyan", width=12)
    for src in sources:
        label = src.replace("_", " ").title()
        if results[src].error:
            label += " [red](err)[/]"
        table.add_column(label, ratio=1)

    for f in _DISPLAY_FIELDS:
        values = [_format_cell(results[src], f) for src in sources]
        if all(v == "[dim]—[/]" for v in values):
            continue
        non_empty = [v for v in values if v != "[dim]—[/]"]
        has_diff = len(set(non_empty)) > 1
        table.add_row(f"[bold yellow]{f}[/]" if has_diff else f, *values)

    console.print(table)

    # ACL BibTeX panel
    acl = results.get("acl_anthology")
    if acl and acl.bibtex:
        console.print()
        console.print(Panel(acl.bibtex, title="BibTeX from ACL Anthology", border_style="green"))

    # Diff summary
    console.print()
    diffs = _compute_diffs(results, sources)
    if diffs:
        console.print("[bold]Diffs:[/]")
        for d in diffs:
            console.print(d)
    else:
        console.print("[green]No diffs between sources.[/]")


# =============================================================================
# Display: JSON
# =============================================================================

_JSON_FIELDS = (
    "source",
    "title",
    "authors",
    "year",
    "venue",
    "entry_type",
    "doi",
    "url",
    "pages",
    "volume",
    "number",
    "extra",
    "error",
    "bibtex",
)


def display_json(results: dict[str, SourceResult]) -> None:
    out = {}
    for name, r in results.items():
        d = {f: getattr(r, f) for f in _JSON_FIELDS}
        d = {k: v for k, v in d.items() if v}  # Drop None/empty
        out[name] = d
    print(json.dumps(out, indent=2, ensure_ascii=False))


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch paper metadata from multiple sources and compare",
        epilog="Sources: Semantic Scholar, CrossRef, DBLP, arXiv, OpenReview, ACL Anthology",
    )
    parser.add_argument("paper_id", help="arXiv ID (2010.11929), DOI (10.xxx/yyy), or Semantic Scholar ID")
    parser.add_argument("--json", action="store_true", help="Output as JSON (for piping to AI agents)")
    parser.add_argument(
        "--sources", help=f"Comma-separated sources to fetch (default: all). Choices: {','.join(ALL_SOURCES)}"
    )
    args = parser.parse_args()

    sources = None
    if args.sources:
        sources = [s.strip() for s in args.sources.split(",")]
        invalid = [s for s in sources if s not in ALL_SOURCES]
        if invalid:
            parser.error(f"Unknown sources: {', '.join(invalid)}. Choose from: {', '.join(ALL_SOURCES)}")

    log = Console(stderr=True)
    results = fetch_all(args.paper_id, log, sources=sources)

    if args.json:
        display_json(results)
    else:
        display_rich(results, Console())


if __name__ == "__main__":
    main()

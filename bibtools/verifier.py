"""Core verification logic."""

import re
from datetime import datetime
from pathlib import Path

from rich.console import Console

from .constants import AUTO_FIND_ID, AUTO_FIND_NONE, AUTO_FIND_TITLE
from .fetcher import MetadataFetcher
from .models import FieldMismatch, PaperMetadata, VerificationReport, VerificationResult
from .parser import (
    extract_paper_id_from_entry,
    generate_verification_comment,
    is_entry_verified,
    parse_bib_file,
)
from .semantic_scholar import ResolvedIds
from .utils import (
    compare_authors,
    compare_titles,
    compare_venues,
    title_similarity,
)


class BibVerifier:
    """Verifies bibtex entries against CrossRef/arXiv (via Semantic Scholar ID resolution)."""

    def __init__(
        self,
        api_key: str | None = None,
        skip_verified: bool = True,
        max_age_days: int | None = None,
        auto_find_level: str = "id",
        fix_errors: bool = False,
        fix_warnings: bool = False,
        arxiv_check: bool = True,
        mark_warnings_verified: bool = False,
        console: Console | None = None,
        *,
        fetcher: MetadataFetcher | None = None,
    ):
        """Initialize the verifier.

        Args:
            api_key: Optional Semantic Scholar API key.
            skip_verified: Skip entries that are already verified.
            max_age_days: Re-verify entries older than this many days. None = never re-verify.
            auto_find_level: Level of auto-find: "none", "id", or "title".
            fix_errors: Automatically fix ERROR fields.
            fix_warnings: Automatically fix WARNING fields.
            arxiv_check: Cross-check with arXiv when arXiv ID exists.
            mark_warnings_verified: Mark WARNING entries as verified (skip on future runs).
            console: Rich console for output.
            fetcher: Optional pre-configured MetadataFetcher (for sharing).
        """
        self._fetcher = fetcher or MetadataFetcher(api_key=api_key)
        self._owns_fetcher = fetcher is None

        self.skip_verified = skip_verified
        self.max_age_days = max_age_days
        self.auto_find_level = auto_find_level
        self.fix_errors = fix_errors
        self.fix_warnings = fix_warnings
        self.arxiv_check = arxiv_check
        self.mark_warnings_verified = mark_warnings_verified
        self.console = console or Console()

        if auto_find_level not in (AUTO_FIND_NONE, AUTO_FIND_ID, AUTO_FIND_TITLE):
            raise ValueError(f"Invalid auto_find_level: {auto_find_level}")

    def close(self) -> None:
        """Close owned fetcher."""
        if self._owns_fetcher:
            self._fetcher.close()

    def __enter__(self) -> "BibVerifier":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _resolve_batch(self, paper_ids: list[str]) -> dict[str, ResolvedIds | None]:
        """Resolve paper IDs via S2 batch API (works for single or multiple IDs)."""
        return self._fetcher.resolve_batch(paper_ids)

    def _fetch_with_resolved(self, resolved: ResolvedIds) -> PaperMetadata | None:
        """Fetch metadata using pre-resolved IDs."""
        return self._fetcher.fetch_with_resolved(resolved)

    def _should_skip_verified(self, date_str: str | None) -> bool:
        """Determine if a verified entry should be skipped based on age.

        Args:
            date_str: Verification date string in YYYY.MM.DD format.

        Returns:
            True if entry should be skipped, False if it should be re-verified.
        """
        # If max_age_days is None, always skip verified entries
        if self.max_age_days is None:
            return True

        # If max_age_days is 0, never skip (always re-verify)
        if self.max_age_days == 0:
            return False

        # If no date string, can't determine age - don't skip (re-verify)
        if not date_str:
            return False

        try:
            verified_date = datetime.strptime(date_str, "%Y.%m.%d")
            age_days = (datetime.now() - verified_date).days
            return age_days <= self.max_age_days
        except ValueError:
            # Invalid date format - don't skip (re-verify)
            return False

    def verify_entry(
        self,
        entry: dict,
        content: str,
    ) -> VerificationResult:
        """Verify a single bibtex entry.

        Flow:
        1. S2 resolves paper_id → DOI/arXiv ID + venue
        2. Source selection (mutually exclusive):
           - if DOI exists        → CrossRef
           - elif venue != arXiv  → DBLP
           - elif venue == arXiv  → arXiv
           - else                 → FAIL (return None)

        Args:
            entry: Bibtex entry dictionary.
            content: Raw file content for checking existing verification.

        Returns:
            Verification result.
        """
        entry_key = entry.get("ID", "unknown")

        # Check if already verified and should skip
        is_verified, date_str, _ = is_entry_verified(content, entry_key)
        if is_verified and self.skip_verified and self._should_skip_verified(date_str):
            return VerificationResult(
                entry_key=entry_key,
                success=True,
                message="Already verified",
                already_verified=True,
            )

        # Extract paper_id from entry (comment, doi/eprint depending on level)
        paper_id, source = extract_paper_id_from_entry(entry, content, self.auto_find_level)
        auto_found = source in ("doi", "eprint", "title") if source else False

        # If no paper_id and title search is enabled, try title search
        if not paper_id and self.auto_find_level == AUTO_FIND_TITLE:
            title = entry.get("title", "")
            if title:
                paper_id, source = self._search_by_title_for_id(entry)
                if paper_id:
                    auto_found = True

        # No paper_id = warning (not failure)
        if not paper_id:
            return VerificationResult(
                entry_key=entry_key,
                success=True,  # Not a failure, just a warning
                message="No paper_id found",
                no_paper_id=True,
            )

        # Use batch resolve (works for single ID too) then verify
        resolved_map = self._resolve_batch([paper_id])
        resolved = resolved_map.get(paper_id)
        return self._verify_entry_with_resolved(entry, paper_id, source or "", auto_found, resolved)

    def _check_field_mismatches(
        self, entry: dict, metadata: PaperMetadata
    ) -> tuple[list[FieldMismatch], list[FieldMismatch]]:
        """Check for mismatches between bibtex entry and fetched metadata.

        Strict matching: only exact string match is PASS.
        - Exact match: PASS
        - Normalized/alias match: WARNING
        - No match: FAIL

        Args:
            entry: Bibtex entry dictionary.
            metadata: Paper metadata from CrossRef/arXiv.

        Returns:
            Tuple of (mismatches, warnings).
            - mismatches: Hard errors (FAIL).
            - warnings: Soft issues (WARNING).
        """
        source = metadata.source
        mismatches = []
        warnings = []

        # Check title
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

        # Check authors
        bib_author_field = entry.get("author", "")
        if bib_author_field and metadata.authors:
            api_author_str = metadata.get_authors_str()  # "Family, Given and ..." format
            # compare_authors expects list of names in bibtex format (Family, Given)
            from .utils import format_author_bibtex_style

            author_names = [
                format_author_bibtex_style(a.get("given", ""), a.get("family", "")) for a in metadata.authors
            ]
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

        # Check year (must be exact)
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

        # Check venue
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

    def _check_arxiv_cross_match(self, arxiv_id: str, metadata: PaperMetadata) -> str | None:
        """Cross-check metadata from CrossRef/DBLP against arXiv.

        This catches cases where DBLP returns the wrong paper (e.g., OpenVLA has
        two different entries in DBLP with different authors).

        Args:
            arxiv_id: arXiv ID to fetch from.
            metadata: Metadata from CrossRef/DBLP.

        Returns:
            Error message if mismatch detected, None if OK.
        """
        try:
            arxiv_meta = self._fetcher.arxiv_client.get_paper_metadata(arxiv_id)
        except Exception:
            # If arXiv fetch fails, skip cross-check (don't fail verification)
            return None

        if not arxiv_meta:
            return None

        # Compare authors - use normalized comparison
        arxiv_authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in arxiv_meta.authors]
        source_authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in metadata.authors]

        # Check if author lists match (normalized)
        from .utils import normalize_author_name

        arxiv_normalized = [normalize_author_name(a) for a in arxiv_authors]
        source_normalized = [normalize_author_name(a) for a in source_authors]

        if arxiv_normalized != source_normalized:
            arxiv_str = ", ".join(arxiv_authors)
            source_str = ", ".join(source_authors)
            return f"authors mismatch - arXiv: [{arxiv_str}] vs {metadata.source}: [{source_str}]"

        return None

    def _search_by_title_for_id(self, entry: dict) -> tuple[str | None, str | None]:
        """Search for paper by title and return paper_id if found with high confidence.

        Args:
            entry: Bibtex entry dictionary.

        Returns:
            Tuple of (paper_id, source). source is "title" if found.
        """
        title = entry.get("title", "")
        if not title:
            return None, None

        from .utils import strip_latex_braces

        search_title = strip_latex_braces(title)

        try:
            resolved_list = self._fetcher.s2_client.search_by_title(search_title, limit=3)
        except ConnectionError:
            return None, None

        if not resolved_list:
            return None, None

        # Find best match by title similarity
        best_match = None
        best_score = 0.0
        for resolved in resolved_list:
            if resolved.title:
                score = title_similarity(title, resolved.title)
                if score > best_score:
                    best_score = score
                    best_match = resolved

        if best_score >= 0.85 and best_match:
            return best_match.paper_id, "title"

        return None, None

    def verify_file(self, file_path: Path, show_progress: bool = True) -> tuple[VerificationReport, str]:
        """Verify all entries in a bibtex file.

        Args:
            file_path: Path to the .bib file.
            show_progress: Whether to show a progress bar.

        Returns:
            Tuple of (verification report, updated content).
        """
        from tqdm import tqdm

        entries, content = parse_bib_file(file_path)
        report = VerificationReport()
        updated_content = content

        # Collect entries to verify
        entries_to_verify: list[tuple[dict, str, str, bool]] = []  # (entry, paper_id, source, auto_found)
        for entry in entries:
            entry_key = entry.get("ID", "unknown")

            # Check if already verified and should skip
            is_verified, date_str, _ = is_entry_verified(content, entry_key)
            if is_verified and self.skip_verified and self._should_skip_verified(date_str):
                report.add_result(
                    VerificationResult(
                        entry_key=entry_key,
                        success=True,
                        message="Already verified",
                        already_verified=True,
                    )
                )
                continue

            # Extract paper_id
            paper_id, source = extract_paper_id_from_entry(entry, content, self.auto_find_level)
            auto_found = source in ("doi", "eprint", "title") if source else False

            # If no paper_id and title search is enabled, try title search
            if not paper_id and self.auto_find_level == AUTO_FIND_TITLE:
                title = entry.get("title", "")
                if title:
                    paper_id, source = self._search_by_title_for_id(entry)
                    if paper_id:
                        auto_found = True

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

            entries_to_verify.append((entry, paper_id, source or "", auto_found))

        if not entries_to_verify:
            return report, updated_content

        # Batch resolve all paper IDs via S2 (single API call)
        paper_ids = [paper_id for _, paper_id, _, _ in entries_to_verify]
        if show_progress:
            self.console.print(f"[dim]Resolving {len(paper_ids)} paper IDs...[/]")
        resolved_map = self._resolve_batch(paper_ids)

        # Verify each entry using pre-resolved IDs
        if show_progress:
            self.console.print(f"[dim]Verifying {len(entries_to_verify)} entries...[/]")
            entry_iter = tqdm(entries_to_verify, desc="Verifying", unit="entry", leave=False)
        else:
            entry_iter = entries_to_verify

        for entry, paper_id, source, auto_found in entry_iter:
            resolved = resolved_map.get(paper_id)
            result = self._verify_entry_with_resolved(entry, paper_id, source, auto_found, resolved)
            report.add_result(result)

            # Add paper_id comment if verified (PASS or WARNING, not FAIL)
            if result.success and result.needs_update and result.metadata and result.paper_id_used:
                if result.fixed and result.mismatches:
                    updated_content = self._apply_field_fixes(
                        updated_content, entry, result.metadata, result.mismatches
                    )
                # PASS: always include "verified via" (skip on future runs)
                # WARNING: include "verified via" only if mark_warnings_verified is set
                is_pass = not result.warnings
                include_verified = is_pass or self.mark_warnings_verified
                updated_content = self._add_verification_comment(
                    updated_content, entry, result.paper_id_used, include_verified=include_verified
                )

        return report, updated_content

    def _verify_entry_with_resolved(
        self,
        entry: dict,
        paper_id: str,
        source: str,
        auto_found: bool,
        resolved: ResolvedIds | None,
    ) -> VerificationResult:
        """Verify entry using pre-resolved IDs from S2 batch API.

        Args:
            entry: Bibtex entry dictionary.
            paper_id: Paper ID used for lookup.
            source: Source of paper_id.
            auto_found: Whether paper_id was auto-found.
            resolved: Pre-resolved IDs from batch API.

        Returns:
            Verification result.
        """
        entry_key = entry.get("ID", "unknown")

        if not resolved:
            return VerificationResult(
                entry_key=entry_key,
                success=False,
                message=f"Paper not found for {paper_id}",
                paper_id_used=paper_id,
                auto_found_paper_id=auto_found,
                paper_id_source=source,
            )

        # Fetch metadata from CrossRef/DBLP/arXiv using pre-resolved IDs
        try:
            metadata = self._fetch_with_resolved(resolved)
        except Exception as e:
            return VerificationResult(
                entry_key=entry_key,
                success=False,
                message=f"API error: {e}",
                paper_id_used=paper_id,
                auto_found_paper_id=auto_found,
                paper_id_source=source,
            )

        if not metadata:
            return VerificationResult(
                entry_key=entry_key,
                success=False,
                message=f"Paper not found for {paper_id}",
                paper_id_used=paper_id,
                auto_found_paper_id=auto_found,
                paper_id_source=source,
            )

        # Cross-check with arXiv if enabled and arXiv ID exists
        # This catches cases where DBLP/CrossRef returns wrong paper (e.g., different authors)
        if self.arxiv_check and resolved.arxiv_id and metadata.source != "arxiv":
            arxiv_mismatch = self._check_arxiv_cross_match(resolved.arxiv_id, metadata)
            if arxiv_mismatch:
                return VerificationResult(
                    entry_key=entry_key,
                    success=False,
                    message=f"arXiv cross-check failed: {arxiv_mismatch}",
                    metadata=metadata,
                    paper_id_used=paper_id,
                    auto_found_paper_id=auto_found,
                    paper_id_source=source,
                )

        # Verify title, authors, year, venue match
        mismatches, warnings = self._check_field_mismatches(entry, metadata)
        return self._build_verification_result(entry, paper_id, source, auto_found, metadata, mismatches, warnings)

    def _build_verification_result(
        self,
        entry: dict,
        paper_id: str,
        source: str,
        auto_found: bool,
        metadata: PaperMetadata,
        mismatches: list[FieldMismatch],
        warnings: list[FieldMismatch],
    ) -> VerificationResult:
        """Build verification result from field comparison."""
        entry_key = entry.get("ID", "unknown")

        if mismatches:
            if self.fix_errors:
                return VerificationResult(
                    entry_key=entry_key,
                    success=True,
                    message="Fixed and verified",
                    metadata=metadata,
                    paper_id_used=paper_id,
                    auto_found_paper_id=auto_found,
                    paper_id_source=source,
                    mismatches=mismatches,
                    warnings=warnings,
                    fixed=True,
                    needs_update=True,
                )
            else:
                mismatch_fields = ", ".join(m.field_name for m in mismatches)
                return VerificationResult(
                    entry_key=entry_key,
                    success=False,
                    message=f"Field mismatch: {mismatch_fields}",
                    metadata=metadata,
                    paper_id_used=paper_id,
                    auto_found_paper_id=auto_found,
                    paper_id_source=source,
                    mismatches=mismatches,
                    warnings=warnings,
                )

        # Handle warnings - fix them if fix_warnings is enabled
        fixed_warnings = self.fix_warnings and bool(warnings)

        message = "Verified"
        if warnings and not self.fix_warnings:
            warning_fields = ", ".join(w.field_name for w in warnings)
            message = f"Verified (warning: {warning_fields} format differs)"
        elif fixed_warnings:
            message = "Fixed warnings and verified"

        return VerificationResult(
            entry_key=entry_key,
            success=True,
            message=message,
            metadata=metadata,
            paper_id_used=paper_id,
            auto_found_paper_id=auto_found,
            paper_id_source=source,
            warnings=warnings if not self.fix_warnings else [],
            mismatches=warnings if self.fix_warnings else [],
            fixed=fixed_warnings,
            needs_update=True,
        )

    def _add_verification_comment(
        self,
        content: str,
        entry: dict,
        paper_id: str,
        include_verified: bool = True,
    ) -> str:
        """Add a verification comment before an entry.

        Args:
            content: File content.
            entry: Bibtex entry dictionary.
            paper_id: Paper ID used for lookup. Required.
            include_verified: If True, include "verified via bibtools (date)" suffix.

        Returns:
            Updated content with verification comment.
        """
        entry_key = entry.get("ID", "")
        # Find the entry in the content - capture leading whitespace, comments, then the entry
        # Pattern: whitespace, optional comments, then the entry
        entry_pattern = re.compile(
            rf"(\s*)((?:%[^\n]*\n)*)(@\w+\{{\s*{re.escape(entry_key)}\s*,)",
            re.MULTILINE,
        )
        match = entry_pattern.search(content)

        if not match:
            return content

        leading_whitespace = match.group(1)
        existing_comments = match.group(2).strip()
        entry_start = match.group(3)

        # Determine the prefix (what comes before this match)
        prefix = content[: match.start()]

        # Generate verification comment with paper_id embedded
        comment = generate_verification_comment(paper_id, include_verified=include_verified)

        # Remove existing paper_id comment if present (any format)
        # Matches: "% paper_id: xxx" or "% paper_id: xxx, verified via ..."
        existing_paper_id_pattern = re.compile(
            r"%\s*paper_id:\s*\S+[^\n]*\n?",
            re.IGNORECASE,
        )

        cleaned_comments = existing_paper_id_pattern.sub("", existing_comments)

        if cleaned_comments.strip():
            new_block = f"{leading_whitespace}{cleaned_comments.strip()}\n{comment}\n{entry_start}"
        else:
            new_block = f"{leading_whitespace}{comment}\n{entry_start}"

        return prefix + new_block + content[match.end() :]

    def _apply_field_fixes(
        self,
        content: str,
        entry: dict,
        metadata: PaperMetadata,
        mismatches: list[FieldMismatch],
    ) -> str:
        """Apply field fixes to an entry.

        Args:
            content: File content.
            entry: Bibtex entry dictionary.
            metadata: Paper metadata from CrossRef/arXiv.
            mismatches: List of field mismatches to fix.

        Returns:
            Updated content with fixed fields.
        """
        entry_key = entry.get("ID", "")

        # Find the full entry in content
        entry_pattern = re.compile(
            rf"(@\w+\{{\s*{re.escape(entry_key)}\s*,.*?\n\}})",
            re.DOTALL,
        )
        match = entry_pattern.search(content)
        if not match:
            return content

        entry_text = match.group(1)
        updated_entry = entry_text

        for mismatch in mismatches:
            field_name = mismatch.field_name
            new_value = mismatch.fetched_value

            if field_name == "title":
                # Replace title field
                updated_entry = self._replace_field(updated_entry, "title", metadata.title or "")
            elif field_name == "author":
                # Replace author field
                authors_str = metadata.get_authors_str()
                updated_entry = self._replace_field(updated_entry, "author", authors_str)
            elif field_name == "year":
                # Replace year field
                updated_entry = self._replace_field(updated_entry, "year", str(metadata.year or ""))
            elif field_name == "venue":
                # Replace journal or booktitle
                if "journal" in entry:
                    updated_entry = self._replace_field(updated_entry, "journal", new_value)
                elif "booktitle" in entry:
                    updated_entry = self._replace_field(updated_entry, "booktitle", new_value)

        return content[: match.start()] + updated_entry + content[match.end() :]

    def _replace_field(self, entry_text: str, field_name: str, new_value: str) -> str:
        """Replace a field value in an entry, handling nested braces, quotes, and bare values."""
        match = re.search(rf"(\s*)({re.escape(field_name)}\s*=\s*)", entry_text, re.IGNORECASE)
        if not match:
            return entry_text

        start = match.end()
        if start >= len(entry_text):
            return entry_text

        open_char = entry_text[start]
        end_pos = -1

        if open_char == "{":
            # Find matching closing brace (handle nested braces)
            depth, i = 1, start + 1
            while i < len(entry_text) and depth > 0:
                if entry_text[i] == "{":
                    depth += 1
                elif entry_text[i] == "}":
                    depth -= 1
                i += 1
            if depth == 0:
                end_pos = i
        elif open_char == '"':
            # Find matching closing quote (simple version, no escaped quotes)
            i = entry_text.find('"', start + 1)
            if i != -1:
                end_pos = i + 1
        else:
            # Handle bare values (like year = 2024). Value ends at comma or closing brace.
            end_match = re.search(r"[,}]", entry_text[start:])
            if end_match:
                end_pos = start + end_match.start()

        if end_pos == -1:
            return entry_text

        new_field = f"{match.group(1)}{match.group(2)}{{{new_value}}}"
        return entry_text[: match.start()] + new_field + entry_text[end_pos:]

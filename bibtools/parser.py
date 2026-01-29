"""Bibtex parsing and manipulation utilities."""

import re
from datetime import date
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

from . import __version__
from .constants import AUTO_FIND_ID, AUTO_FIND_NONE

# Regex patterns for paper_id comments
# Format 1: "% paper_id: {paper_id}" (unverified, just paper_id)
# Format 2: "% paper_id: {paper_id}, verified via {verifier} (YYYY.MM.DD)" (verified)
# Note: verifier can be any identifier (bibtools, Claude, human, etc.)
# Date is REQUIRED for verification - entries without date are treated as unverified
PAPER_ID_PATTERN = re.compile(
    r"^%\s*paper_id:\s*(\S+?)(?:,\s*verified\s+via\s+(\S+)\s*\((\d{4}\.\d{2}\.\d{2})\))?$",
    re.IGNORECASE,
)

# Pattern to detect "verified via" without date (for error messages)
MISSING_DATE_PATTERN = re.compile(
    r"^%\s*paper_id:\s*\S+?,\s*verified\s+via\s+\S+\s*$",
    re.IGNORECASE,
)


def parse_bib_file(file_path: Path) -> tuple[list[dict], str]:
    """Parse a bibtex file and return entries with raw content.

    Args:
        file_path: Path to the .bib file.

    Returns:
        Tuple of (list of entries, raw file content).
    """
    content = file_path.read_text(encoding="utf-8")

    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode

    bib_database = bibtexparser.loads(content, parser=parser)

    return bib_database.entries, content


def get_entry_comments(content: str, entry_key: str) -> str | None:
    """Get comment lines preceding a bibtex entry.

    Args:
        content: Raw file content.
        entry_key: Bibtex entry key.

    Returns:
        Comment lines as a string, or None if entry not found.
    """
    entry_pattern = re.compile(
        rf"((?:%[^\n]*\n)*)\s*@\w+\{{\s*{re.escape(entry_key)}\s*,",
        re.MULTILINE,
    )
    match = entry_pattern.search(content)
    if not match:
        return None
    return match.group(1)


def is_entry_verified(content: str, entry_key: str) -> tuple[bool, str | None, str | None]:
    """Check if an entry has a verification comment.

    Args:
        content: Raw file content.
        entry_key: Bibtex entry key.

    Returns:
        Tuple of (is_verified, date_str, paper_id).
        - is_verified: True if verified with date (verified via {verifier} (YYYY.MM.DD))
        - date_str: Verification date in YYYY.MM.DD format (None if unverified)
        - paper_id: Paper ID from the comment (may be None if not found)
    """
    comments = get_entry_comments(content, entry_key)
    if not comments:
        return False, None, None

    for line in comments.strip().split("\n"):
        line_stripped = line.strip()
        match = PAPER_ID_PATTERN.match(line_stripped)
        if match:
            paper_id = match.group(1)
            verifier = match.group(2)  # verifier name or None
            date_str = match.group(3)  # YYYY.MM.DD or None
            # Entry is verified only if both verifier and date are present
            is_verified = verifier is not None and date_str is not None
            return is_verified, date_str, paper_id

    return False, None, None


def has_missing_date(content: str, entry_key: str) -> bool:
    """Check if an entry has 'verified via' without a date.

    Args:
        content: Raw file content.
        entry_key: Bibtex entry key.

    Returns:
        True if entry has 'verified via {verifier}' without date.
    """
    comments = get_entry_comments(content, entry_key)
    if not comments:
        return False

    for line in comments.strip().split("\n"):
        line_stripped = line.strip()
        if MISSING_DATE_PATTERN.match(line_stripped):
            return True

    return False


def extract_paper_id_from_comments(content: str, entry_key: str) -> str | None:
    """Extract paper_id from comment.

    Formats:
    - "% paper_id: {id}" (unverified)
    - "% paper_id: {id}, verified via {verifier} (YYYY.MM.DD)" (verified)

    Args:
        content: Raw file content.
        entry_key: Bibtex entry key.

    Returns:
        Paper ID string (e.g., "ARXIV:2106.15928") or None.
    """
    comments = get_entry_comments(content, entry_key)
    if not comments:
        return None

    for line in comments.strip().split("\n"):
        line_stripped = line.strip()
        match = PAPER_ID_PATTERN.match(line_stripped)
        if match:
            return match.group(1)

    return None


def extract_paper_id_from_entry(
    entry: dict, content: str, auto_find_level: str = AUTO_FIND_ID
) -> tuple[str | None, str | None]:
    """Extract paper_id from entry fields or comments.

    Priority: comment paper_id > doi field > eprint field

    Args:
        entry: Bibtex entry dictionary.
        content: Raw file content.
        auto_find_level: Level of auto-find: "none", "id", or "title".

    Returns:
        Tuple of (paper_id, source). Source is "comment", "doi", "eprint", or None.
        Note: "title" source is handled separately in verifier (requires API call).
    """
    entry_key = entry.get("ID", "")

    # 1. Check comment for explicit paper_id
    paper_id = extract_paper_id_from_comments(content, entry_key)
    if paper_id:
        return paper_id, "comment"

    # If auto_find_level is "none", stop here
    if auto_find_level == AUTO_FIND_NONE:
        return None, None

    # Levels "id" and "title" allow doi/eprint lookup
    # 2. Check doi field
    doi = entry.get("doi", "")
    if doi:
        # Remove URL prefix if present
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        return f"DOI:{doi}", "doi"

    # 3. Check eprint field (arXiv)
    eprint = entry.get("eprint", "")
    if eprint:
        # Clean up the ID
        eprint = eprint.replace("arXiv:", "").strip()
        return f"ARXIV:{eprint}", "eprint"

    # Title search is handled in verifier (requires API call)
    return None, None


def generate_verification_comment(paper_id: str, include_verified: bool = True) -> str:
    """Generate verification comment line.

    Args:
        paper_id: Paper ID used for lookup (e.g., "ARXIV:2106.15928").
        include_verified: If True, include "verified via bibtools@version (date)" suffix.
                          If False, only include paper_id.

    Returns:
        Single-line verification comment string.
        - With include_verified=True: "% paper_id: {paper_id}, verified via bibtools@x.y.z (YYYY.MM.DD)"
        - With include_verified=False: "% paper_id: {paper_id}"
    """
    if include_verified:
        today = date.today().strftime("%Y.%m.%d")
        return f"% paper_id: {paper_id}, verified via bibtools v{__version__} ({today})"
    else:
        return f"% paper_id: {paper_id}"


def insert_paper_id_comment(
    content: str,
    entry_key: str,
    paper_id: str,
    *,
    include_verified: bool = False,
    extra_comments: list[str] | None = None,
) -> str:
    """Insert or replace paper_id comment for a bibtex entry.

    Args:
        content: Raw file content.
        entry_key: Bibtex entry key.
        paper_id: Paper ID string.
        include_verified: If True, include "verified via bibtools vX.Y.Z (YYYY.MM.DD)".
        extra_comments: Optional list of extra single-line comments (without leading "%").

    Returns:
        Updated content with the paper_id comment inserted or updated.
    """
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

    prefix = content[: match.start()]

    comment = generate_verification_comment(paper_id, include_verified=include_verified)

    # Remove existing paper_id comments (any format)
    existing_paper_id_pattern = re.compile(
        r"%\s*paper_id:\s*\S+[^\n]*\n?",
        re.IGNORECASE,
    )
    cleaned_comments = existing_paper_id_pattern.sub("", existing_comments)

    extra_lines = []
    if extra_comments:
        for extra in extra_comments:
            extra_line = extra.strip()
            if not extra_line:
                continue
            if extra_line.startswith("%"):
                extra_lines.append(extra_line)
            else:
                extra_lines.append(f"% {extra_line}")

    comments_block_parts = []
    if cleaned_comments.strip():
        comments_block_parts.append(cleaned_comments.strip())
    comments_block_parts.append(comment)
    comments_block_parts.extend(extra_lines)

    comments_block = "\n".join(comments_block_parts)
    new_block = f"{leading_whitespace}{comments_block}\n{entry_start}"

    return prefix + new_block + content[match.end() :]

"""Bibtex parsing and manipulation utilities."""

import re
from datetime import date
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

from .constants import AUTO_FIND_ID, AUTO_FIND_NONE

# Regex patterns for paper_id comments
# Format 1: "% paper_id: {paper_id}" (unverified, just paper_id)
# Format 2: "% paper_id: {paper_id}, verified via bibtools (YYYY.MM.DD)"
# Format 3: "% paper_id: {paper_id}, verified via human({name}) (YYYY.MM.DD)"
# Note: human may have optional space before parentheses: "human(name)" or "human (name)"
PAPER_ID_PATTERN = re.compile(
    r"^%\s*paper_id:\s*(\S+?)(?:,\s*verified\s+via\s+(bibtools|human\s*\([^)]+\))\s*\((\d{4}\.\d{2}\.\d{2})\))?$",
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
        - is_verified: True if verified via bibtools or human
        - date_str: Verification date in YYYY.MM.DD format (None if unverified)
        - paper_id: Paper ID from the comment (may be None if unverified)
    """
    comments = get_entry_comments(content, entry_key)
    if not comments:
        return False, None, None

    for line in comments.strip().split("\n"):
        line_stripped = line.strip()
        match = PAPER_ID_PATTERN.match(line_stripped)
        if match:
            paper_id = match.group(1)
            verifier = match.group(2)  # "bibtools" or "human(...)" or None
            date_str = match.group(3)  # YYYY.MM.DD or None
            # Entry is verified if verifier is present
            is_verified = verifier is not None
            return is_verified, date_str, paper_id

    return False, None, None


def extract_paper_id_from_comments(content: str, entry_key: str) -> str | None:
    """Extract paper_id from comment.

    Formats:
    - "% paper_id: {id}" (unverified)
    - "% paper_id: {id}, verified via bibtools (YYYY.MM.DD)"
    - "% paper_id: {id}, verified via human({name}) (YYYY.MM.DD)"

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
        include_verified: If True, include "verified via bibtools (date)" suffix.
                          If False, only include paper_id.

    Returns:
        Single-line verification comment string.
        - With include_verified=True: "% paper_id: {paper_id}, verified via bibtools (YYYY.MM.DD)"
        - With include_verified=False: "% paper_id: {paper_id}"
    """
    if include_verified:
        today = date.today().strftime("%Y.%m.%d")
        return f"% paper_id: {paper_id}, verified via bibtools ({today})"
    else:
        return f"% paper_id: {paper_id}"

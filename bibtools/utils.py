"""String processing utilities for bibtools."""

import re
from difflib import SequenceMatcher


def strip_latex_braces(title: str) -> str:
    """Strip LaTeX braces from title.

    Removes {} and $ characters only.
    """
    title = re.sub(r"[{}$]", "", title)
    # Normalize whitespace only
    return " ".join(title.split())


def title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles (case-insensitive for similarity score)."""
    t1 = strip_latex_braces(title1).lower()
    t2 = strip_latex_braces(title2).lower()
    return SequenceMatcher(None, t1, t2).ratio()


def compare_titles(bib_title: str, ss_title: str) -> tuple[bool, bool]:
    """Compare titles for match.

    PASS is extremely conservative - only exact match is PASS.

    Args:
        bib_title: Title from bibtex entry.
        ss_title: Title from Semantic Scholar.

    Returns:
        Tuple of (match, warning_only).
        - match=True, warning_only=False: Exact raw string match (PASS).
        - match=True, warning_only=True: Same content but format differs (WARNING).
          Includes: LaTeX braces difference, case difference.
        - match=False, warning_only=False: Real mismatch (FAIL).
    """
    # PASS: Only if raw strings are exactly identical
    if bib_title == ss_title:
        return True, False

    # Strip LaTeX braces and normalize whitespace for content comparison
    bib_stripped = strip_latex_braces(bib_title)
    ss_stripped = strip_latex_braces(ss_title)

    # Case-insensitive match after stripping braces -> WARNING
    # This includes: brace differences, case differences, or both
    if bib_stripped.lower() == ss_stripped.lower():
        return True, True  # match=True but warning=True

    # Real mismatch -> FAIL
    return False, False


def normalize_author_name(name: str) -> str:
    """Normalize an author name for style-only comparison.

    Handles format differences only:
    - "Smith, John" -> "John Smith" (comma format to space format)
    - Removes LaTeX commands and braces
    - Normalizes whitespace

    Does NOT change case or abbreviate names. Only style normalization.
    """
    # Remove LaTeX commands and braces
    name = re.sub(r"\\[a-zA-Z]+", "", name)
    name = re.sub(r"[{}]", "", name)
    # Normalize whitespace
    name = " ".join(name.split())
    # Convert "Last, First" to "First Last"
    if "," in name:
        parts = name.split(",", 1)
        name = f"{parts[1].strip()} {parts[0].strip()}"
    return name


def parse_bibtex_authors(author_field: str) -> list[str]:
    """Parse bibtex author field into list of author names.

    Handles "and" separator.
    """
    if not author_field:
        return []
    # Split by " and " (case insensitive)
    authors = re.split(r"\s+and\s+", author_field, flags=re.IGNORECASE)
    return [a.strip() for a in authors if a.strip()]


def compare_authors(bib_author_field: str, ss_authors: list[str]) -> tuple[bool, bool]:
    """Compare bibtex author field with Semantic Scholar authors.

    Args:
        bib_author_field: Raw author field from bibtex (e.g., "Smith, John and Doe, Jane")
        ss_authors: List of author names from Semantic Scholar (e.g., ["John Smith", "Jane Doe"])

    Returns:
        Tuple of (match, warning_only).
        - match=True, warning_only=False: Exact string match (PASS).
        - match=True, warning_only=True: Style-normalized match (WARNING).
        - match=False, warning_only=False: Real mismatch (FAIL).
    """
    ss_author_str = " and ".join(ss_authors)

    # PASS: Exact raw string match
    if bib_author_field == ss_author_str:
        return True, False

    # Check style-normalized match
    bib_authors = parse_bibtex_authors(bib_author_field)

    if len(bib_authors) != len(ss_authors):
        return False, False

    for bib_author, ss_author in zip(bib_authors, ss_authors):
        bib_normalized = normalize_author_name(bib_author)
        ss_normalized = normalize_author_name(ss_author)
        if bib_normalized != ss_normalized:
            return False, False

    # Style-normalized match -> WARNING
    return True, True


def compare_venues(bib_venue: str, fetched_venue: str) -> tuple[bool, bool]:
    """Compare venue fields.

    Args:
        bib_venue: Venue from bibtex entry.
        fetched_venue: Venue from CrossRef/arXiv (source of truth).

    Returns:
        Tuple of (match, warning_only).
        - match=True, warning_only=False: Exact string match (PASS).
        - match=True, warning_only=True: Alias match (WARNING).
        - match=False, warning_only=False: No match (FAIL).
    """
    from .venue_aliases import venues_match

    # PASS: Exact raw string match
    if bib_venue == fetched_venue:
        return True, False

    # Check alias match
    if venues_match(bib_venue, fetched_venue):
        return True, True  # Alias match -> WARNING

    return False, False


def format_author_bibtex_style(given: str, family: str) -> str:
    """Format author name in bibtex style: Lastname, Firstname.

    Args:
        given: Given name(s).
        family: Family name.

    Returns:
        Formatted author string: "Family, Given"
    """
    return f"{family}, {given}"

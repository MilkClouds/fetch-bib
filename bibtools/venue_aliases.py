"""Venue alias configuration for matching different venue name formats."""

# Each key is a canonical (short) venue name, values are aliases (including the canonical name itself)
# All comparisons are done in lowercase
VENUE_ALIASES: dict[str, set[str]] = {
    # Robotics
    "CoRL": {"corl", "conference on robot learning"},
    "ICRA": {
        "icra",
        "ieee international conference on robotics and automation",
        "international conference on robotics and automation",
    },
    "IROS": {
        "iros",
        "ieee/rsj international conference on intelligent robots and systems",
        "intelligent robots and systems",
    },
    "RSS": {"rss", "robotics: science and systems"},
    "RA-L": {"ral", "ra-l", "ieee robotics and automation letters"},
    "IJRR": {"ijrr", "international journal of robotics research"},
    "TRO": {"tro", "ieee transactions on robotics"},
    # Machine Learning
    "NeurIPS": {
        "neurips",
        "nips",
        "neural information processing systems",
        "advances in neural information processing systems",
    },
    "ICML": {"icml", "international conference on machine learning"},
    "ICLR": {"iclr", "international conference on learning representations"},
    "AAAI": {"aaai", "aaai conference on artificial intelligence"},
    "IJCAI": {"ijcai", "international joint conference on artificial intelligence"},
    "JMLR": {"jmlr", "journal of machine learning research"},
    "TMLR": {
        "tmlr",
        "transactions on machine learning research",
        "trans. mach. learn. res.",
        "trans mach learn res",
    },
    # Computer Vision
    "CVPR": {
        "cvpr",
        "ieee/cvf conference on computer vision and pattern recognition",
        "ieee conference on computer vision and pattern recognition",
        "conference on computer vision and pattern recognition",
    },
    "ICCV": {
        "iccv",
        "ieee/cvf international conference on computer vision",
        "ieee international conference on computer vision",
    },
    "ECCV": {"eccv", "european conference on computer vision"},
    "TPAMI": {"tpami", "ieee transactions on pattern analysis and machine intelligence"},
    # NLP
    "ACL": {
        "acl",
        "annual meeting of the association for computational linguistics",
        "association for computational linguistics",
    },
    "EMNLP": {
        "emnlp",
        "empirical methods in natural language processing",
        "conference on empirical methods in natural language processing",
    },
    "NAACL": {"naacl", "north american chapter of the association for computational linguistics"},
    "TACL": {"tacl", "transactions of the association for computational linguistics"},
    # General AI/CS
    "Nature": {"nature"},
    "Science": {"science"},
    "arXiv": {"arxiv", "arxiv preprint"},
}


def normalize_venue(venue: str) -> str:
    """Normalize venue name for comparison.

    Args:
        venue: Raw venue name.

    Returns:
        Normalized venue name (lowercase, stripped).
    """
    return venue.lower().strip()


def get_canonical_venue(venue: str) -> str | None:
    """Get the canonical venue name for a given venue string.

    Args:
        venue: Venue name to look up.

    Returns:
        Canonical venue name if found, None otherwise.
    """
    normalized = normalize_venue(venue)
    for canonical, aliases in VENUE_ALIASES.items():
        if normalized in aliases:
            return canonical
    return None


def venues_match(venue1: str, venue2: str) -> bool:
    """Check if two venue names match (including aliases).

    Args:
        venue1: First venue name.
        venue2: Second venue name.

    Returns:
        True if venues match (same or aliases), False otherwise.
    """
    norm1 = normalize_venue(venue1)
    norm2 = normalize_venue(venue2)

    # Direct match
    if norm1 == norm2:
        return True

    # Check if both map to the same canonical venue
    canonical1 = get_canonical_venue(venue1)
    canonical2 = get_canonical_venue(venue2)

    if canonical1 and canonical2:
        return canonical1 == canonical2

    # Check if one is a substring of the other (for partial matches)
    # e.g., "CoRL 2023" contains "CoRL"
    if canonical1 and canonical1.lower() in norm2:
        return True
    if canonical2 and canonical2.lower() in norm1:
        return True

    # Check alias sets: both venues must match the same alias group
    for aliases in VENUE_ALIASES.values():
        match1 = any(a in norm1 for a in aliases)
        match2 = any(a in norm2 for a in aliases)
        if match1 and match2:
            return True

    return False


def get_dblp_search_venue(venue: str) -> str:
    """Get venue name suitable for DBLP search queries.

    DBLP uses historical venue names (e.g., "NIPS" instead of "NeurIPS").

    Args:
        venue: Venue name to convert.

    Returns:
        Venue name for DBLP search.
    """
    canonical = get_canonical_venue(venue)
    resolved = canonical if canonical else venue

    # DBLP uses "NIPS" for NeurIPS papers
    if resolved.upper() == "NEURIPS":
        return "NIPS"

    return resolved


def get_dblp_search_variants(venue: str | None) -> list[str]:
    """Return venue variants to try in DBLP title search."""
    if not venue:
        return []

    variants: list[str] = []
    canonical = get_canonical_venue(venue)
    if canonical:
        variants.append(get_dblp_search_venue(canonical))
        aliases = VENUE_ALIASES.get(canonical, set())
        variants.extend(sorted(aliases))
    variants.append(get_dblp_search_venue(venue))

    # De-dup while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for v in variants:
        v = v.strip()
        if not v or v.lower() in seen:
            continue
        seen.add(v.lower())
        ordered.append(v)
    return ordered


def get_venue_short(venue: str, max_len: int = 50) -> str:
    """Get a short venue name for display (e.g., verification comments).

    Args:
        venue: Raw venue name from Semantic Scholar.
        max_len: Maximum length before truncation.

    Returns:
        Short canonical venue name if found, otherwise truncated original.
    """
    if not venue:
        return ""

    # Try to find canonical short name
    canonical = get_canonical_venue(venue)
    if canonical:
        return canonical

    # Fallback: truncate if too long
    return venue[:max_len] if len(venue) > max_len else venue

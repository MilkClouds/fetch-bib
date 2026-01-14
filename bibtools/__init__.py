"""verify-bib: CLI tool to verify bibtex entries using Semantic Scholar API."""

# Version is managed by hatch-vcs from Git tags
try:
    from ._version import __version__
except ImportError:  # pragma: no cover
    # Fallback for editable installs without build
    try:
        from importlib.metadata import version

        __version__ = version("bibtools")
    except Exception:
        __version__ = "0.0.0.dev0"

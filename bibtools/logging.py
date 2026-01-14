"""Conditional logging for bibtools."""

import os
import sys

_DEBUG = os.environ.get("BIBTOOLS_DEBUG", "").lower() in ("1", "true", "yes")


def debug(msg: str) -> None:
    if _DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    if _DEBUG:
        print(f"[INFO] {msg}", file=sys.stderr)


def warning(msg: str) -> None:
    if _DEBUG:
        print(f"[WARN] {msg}", file=sys.stderr)

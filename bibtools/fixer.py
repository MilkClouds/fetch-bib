"""Bibtex field fix helpers used by review workflows."""

from __future__ import annotations

import re

from .models import FieldMismatch, PaperMetadata


def apply_field_fixes(content: str, entry: dict, metadata: PaperMetadata, fixes: list[FieldMismatch]) -> str:
    """Apply selected field fixes to bibtex content for a single entry."""
    entry_key = entry.get("ID", "")
    entry_pattern = re.compile(
        rf"(@\\w+\\{{\\s*{re.escape(entry_key)}\\s*,.*?\\n\\}})",
        re.DOTALL,
    )
    match = entry_pattern.search(content)
    if not match:
        return content

    entry_text = match.group(1)
    updated_entry = entry_text

    for fix in fixes:
        field = fix.field_name
        if field == "title":
            updated_entry = _replace_field(updated_entry, "title", metadata.title or "")
        elif field == "author":
            updated_entry = _replace_field(updated_entry, "author", metadata.get_authors_str())
        elif field == "year":
            updated_entry = _replace_field(updated_entry, "year", str(metadata.year or ""))
        elif field == "venue":
            new_value = metadata.venue or ""
            if "journal" in entry:
                updated_entry = _replace_field(updated_entry, "journal", new_value)
            elif "booktitle" in entry:
                updated_entry = _replace_field(updated_entry, "booktitle", new_value)

    return content[: match.start()] + updated_entry + content[match.end() :]


def _replace_field(entry_text: str, field_name: str, new_value: str) -> str:
    """Replace a field value in an entry, handling nested braces, quotes, and bare values."""
    match = re.search(rf"(\\s*)({re.escape(field_name)}\\s*=\\s*)", entry_text, re.IGNORECASE)
    if not match:
        return entry_text

    start = match.end()
    if start >= len(entry_text):
        return entry_text

    open_char = entry_text[start]
    end_pos = -1

    if open_char == "{":
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
        i = entry_text.find('"', start + 1)
        if i != -1:
            end_pos = i + 1
    else:
        end_match = re.search(r"[,}]", entry_text[start:])
        if end_match:
            end_pos = start + end_match.start()

    if end_pos == -1:
        return entry_text

    new_field = f"{match.group(1)}{match.group(2)}{{{new_value}}}"
    return entry_text[: match.start()] + new_field + entry_text[end_pos:]

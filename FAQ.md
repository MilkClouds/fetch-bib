# FAQ & Troubleshooting

## Limitations

bibtools relies on external APIs (Semantic Scholar, CrossRef, DBLP, arXiv). When these sources have incomplete or inconsistent data, verification may fail even for correct entries.

### "Paper not found" for a valid paper

**Cause**: The paper is not indexed in Semantic Scholar, or Semantic Scholar doesn't have the DOI/arXiv ID mapping.

**Solutions**:
```bibtex
% Try specifying DOI directly instead of arXiv ID
% paper_id: DOI:10.18653/v1/2025.acl-long.1065

% Or mark as manually verified (only IF YOU HAVE VERIFIED IT MANUALLY)
% paper_id: ARXIV:2406.11317, verified via human (2025.01.20)
```

### "arXiv cross-check failed: authors mismatch"

**Cause**: The author list differs between arXiv (preprint) and the published version. Common for:
- Large collaboration papers (100+ authors)
- Papers where authors were added/removed between preprint and publication

**Solutions**:
```bash
# Disable arXiv cross-check
bibtools verify main.bib --no-arxiv-check
```

```bibtex
% Or mark as manually verified (only IF YOU HAVE VERIFIED IT MANUALLY)
% paper_id: ARXIV:2310.08864, verified via human (2025.01.20)
```

### Year/venue mismatch (preprint vs published)

**Cause**: bibtools found the paper via arXiv but your entry has published venue info.

This happens when:
- Semantic Scholar returns `doi=None`
- DBLP doesn't have the paper yet
- Only arXiv metadata is available

**Solutions**:
```bibtex
% Specify DOI directly to get published metadata
% paper_id: DOI:10.18653/v1/2025.acl-long.1065

% Or accept as WARNING and mark as verified (only IF YOU HAVE VERIFIED IT MANUALLY)
% paper_id: ARXIV:2406.11317, verified via human (2025.01.20)
```

---

## Verification Behavior

### Status: PASS / WARNING / FAIL

| Status | Exit | Meaning |
|--------|------|---------|
| **PASS** | 0 | All fields match |
| **WARNING** | 1 | Tolerable mismatch (format/case differs) |
| **FAIL** | 2 | Content mismatch or error |

### Field Comparison Rules

| Field | PASS | WARNING | FAIL |
|-------|------|---------|------|
| **title** | Exact match | Case/braces differ | Content mismatch |
| **author** | Exact match | Format differs | Content mismatch |
| **year** | Exact match | - | Mismatch |
| **venue** | Exact match | Alias match | Mismatch |

Examples:
- `{Deep Learning}` vs `Deep Learning` → WARNING (braces)
- `Smith, John` vs `John Smith` → WARNING (format)
- `M. Posner` vs `Michael Posner` → FAIL (abbreviation = content change)
- `NeurIPS` vs `Neural Information Processing Systems` → WARNING (alias)

---

## Comment Format

```bibtex
% paper_id: ARXIV:2106.15928, verified via bibtools (2025.01.06)
@inproceedings{example2024,
  title = {Example Paper},
  ...
}
```

**Format:** `% paper_id: {id}, verified via {verifier} (YYYY.MM.DD)`

States:
- `% paper_id: ARXIV:xxx` — unverified (will be re-verified)
- `% paper_id: ARXIV:xxx, verified via bibtools (YYYY.MM.DD)` — verified (skipped)
- `% paper_id: ARXIV:xxx, verified via human (YYYY.MM.DD)` — manually verified
- `% paper_id: SKIP, verified via human (YYYY.MM.DD)` — skip entry (tech reports, etc.)

---

## Auto-find Levels

| Level | Sources | Use case |
|-------|---------|----------|
| `none` | `% paper_id:` comment only | Strict, required for `--fix-*` |
| `id` | comment > `doi` > `eprint` | Default |
| `title` | Above + title search | Risky |

---

## Options Reference

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without modifying |
| `--auto-find=none/id/title` | Paper ID discovery (default: id) |
| `--fix-errors` | Auto-fix ERROR fields (requires --auto-find=none) |
| `--fix-warnings` | Auto-fix WARNING fields (requires --auto-find=none) |
| `--no-arxiv-check` | Disable arXiv cross-check |
| `--mark-warnings-verified` | Mark WARNING entries as verified |
| `--reverify` | Re-verify all entries |
| `--max-age=N` | Re-verify entries older than N days |
| `-o FILE` | Output to different file |
| `--api-key` | Semantic Scholar API key |

---

## Rate Limits

| API | Limit |
|-----|-------|
| Semantic Scholar | 1 req/sec (with key), 100 req/5min (no key) |
| CrossRef | 50 req/sec |
| arXiv | No official limit |

Set `SEMANTIC_SCHOLAR_API_KEY` for faster requests.


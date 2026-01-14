# bibtools

**Automated bibtex verification tool** - validates your bibtex entries against official sources (CrossRef, arXiv).

## What it does

1. **verify** - Compare existing .bib entries against official metadata
2. **fetch** - Generate bibtex from DOI or arXiv ID
3. **search** - Search papers by title and generate bibtex

## How it works

```
bibtools verify main.bib
        ↓
Skip already verified entries (% paper_id: ..., verified via ...)
        ↓
Extract paper_id (DOI/arXiv ID) from each entry
        ↓
Semantic Scholar → Resolve to DOI/arXiv ID + venue
        ↓
    ┌─────────────────────────────────────────┐
    │ if DOI exists       → CrossRef          │
    │ elif venue != arXiv → DBLP              │
    │ elif venue == arXiv → arXiv             │
    │ else                → FAIL              │
    └─────────────────────────────────────────┘
        ↓
Cross-check with arXiv (if arXiv ID exists, --no-arxiv-check to disable)
  → FAIL if authors mismatch between source and arXiv
        ↓
Compare with existing entry → PASS / WARNING / FAIL
```

**Data sources (Single Source of Truth):**

| Condition | Source |
|-----------|--------|
| DOI exists | **CrossRef** |
| No DOI, venue != arXiv | **DBLP** |
| No DOI, venue == arXiv | **arXiv** |

- **Semantic Scholar** - ID resolution + venue detection (determines which source to use)

## Is it reliable?

bibtools does **NOT generate or guess metadata**.
It uses data from official sources only:
- **CrossRef** - Official DOI registry (publisher-submitted)
- **DBLP** - Computer science bibliography (for venues without DOI like ICLR)
- **arXiv** - Preprint source

Semantic Scholar is used only for identifier resolution, not as a metadata source.

→ [Comparison with Google Scholar/Official sources](comparison.md)

---

## Installation

```bash
uv tool install git+https://github.com/MilkClouds/bibtools
```

## Quick Start

```bash
bibtools fetch 2106.09685             # LoRA - auto-detects arXiv ID, gets ICLR 2022 from DBLP
bibtools fetch DOI:10.1109/CVPR.2016.90  # Fetch by DOI
bibtools verify main.bib              # Verify existing entries
bibtools search "Attention Is All You Need"  # Search (use with caution)
```

## Commands

### verify

Verifies bibtex entries against official metadata from CrossRef/DBLP/arXiv.

```bash
bibtools verify main.bib                      # Default: --auto-find=id
bibtools verify main.bib --auto-find=none     # Strict: comment only
bibtools verify main.bib --auto-find=none --fix-errors    # Fix errors
bibtools verify main.bib --auto-find=none --fix-warnings  # Fix warnings (venue, case)
```

### fetch

Fetches bibtex by paper ID. Metadata from CrossRef (DOI) → DBLP → arXiv.

```bash
bibtools fetch 2106.09685                    # LoRA - DBLP (ICLR 2022)
bibtools fetch DOI:10.18653/v1/N18-3011      # CrossRef (ACL)
bibtools fetch DOI:10.1109/CVPR.2016.90      # CrossRef (CVPR)
bibtools fetch ARXIV:2303.08774              # arXiv (GPT-4 - preprint)
```

### search

Searches papers and generates bibtex. **Use with caution** - results may not match your intended paper.

```bash
bibtools search "Attention Is All You Need" --limit 3
```

## Verification Logic

### Status: PASS / WARNING / FAIL

| Status | Exit | Meaning |
|--------|------|---------|
| **PASS** | 0 | All fields match |
| **WARNING** | 1 | Tolerable mismatch (format/case differs) |
| **FAIL** | 2 | Content mismatch or error |

Overall result = worst individual status.

### Field Comparison

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

## Comment Format

```bibtex
% paper_id: ARXIV:2106.15928, verified via bibtools (2025.01.06)
@inproceedings{example2024,
  title = {Example Paper},
  ...
}
```

States:
- `% paper_id: ARXIV:xxx` - paper_id only (WARNING result, will be re-verified)
- `% paper_id: ARXIV:xxx, verified via bibtools (YYYY.MM.DD)` - PASS (skipped on future runs)
- `% paper_id: DOI:xxx, verified via human(Name) (YYYY.MM.DD)` - human verified

**Verification comment behavior:**
- **PASS**: Adds `verified via bibtools (date)` → skipped on future runs
- **WARNING**: Adds `paper_id` only → re-verified on future runs
- Use `--mark-warnings-verified` to mark WARNING as verified (skip future re-verification)

## Auto-find Levels

| Level | Sources | Use case |
|-------|---------|----------|
| `none` | `% paper_id:` comment only | Strict, required for `--fix-*` |
| `id` | comment > `doi` > `eprint` | Default |
| `title` | Above + title search | Risky |

Auto-found paper_id is written on PASS and WARNING.

## Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview without modifying |
| `--auto-find=none/id/title` | Paper ID discovery (default: id) |
| `--fix-errors` | Auto-fix ERROR fields (requires --auto-find=none) |
| `--fix-warnings` | Auto-fix WARNING fields (requires --auto-find=none) |
| `--mark-warnings-verified` | Mark WARNING entries as verified (skip future runs) |
| `--reverify` | Re-verify verified entries |
| `--max-age=N` | Re-verify entries older than N days |
| `-o FILE` | Output to different file |
| `--api-key` | Semantic Scholar API key |

## Supported Paper IDs

- `ARXIV:2106.15928`
- `DOI:10.18653/v1/N18-3011`
- `CorpusId:215416146`
- `ACL:W12-3903`
- `PMID:19872477`

## Rate Limits

| API | Limit | Implementation |
|-----|-------|----------------|
| Semantic Scholar | 1 req/sec (with key), 100 req/5min (no key) | 1s or 3s interval |
| CrossRef | 50 req/sec (official) | 0.02s interval (50 req/sec) |
| arXiv | No official limit | No throttling |

Set `SEMANTIC_SCHOLAR_API_KEY` environment variable or use `--api-key` for faster requests.

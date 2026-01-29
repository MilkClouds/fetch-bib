# bibtools

**Automated bibtex verification tool** — validate and fetch bibtex entries from official sources (CrossRef, DBLP, arXiv).

## Why?

**Google Scholar and Semantic Scholar have errors across all fields** (tested on [13 papers](comparison.md)):

| | GS | S2 | bibtools |
|---|---|---|---|
| venue | 6/13 wrong (arXiv) | 7/13 wrong (arXiv) | 1/13 wrong* |
| year | 1/13 wrong | 5/13 wrong | ✓ |
| title | Lowercases acronyms | ✓ | ✓ |
| author | Truncates ("and others") | Abbreviates, missing/extra | ✓ |

\* FLOWER (CoRL 2025) — too recent for DBLP/S2 to have updated

**Official sources are the best available baseline**, but they can still contain errors. bibtools gives you a strict, transparent workflow and an interactive review step when data conflicts.

**bibtools matches official sources** by fetching from CrossRef/DBLP/arXiv directly:

| Paper | Venue | GS | S2 | Official | bibtools |
|-------|-------|:--:|:--:|:--------:|:--------:|
| ResNet | CVPR 2016 | ✓ | ✗ year | ✓ | ✓ |
| Attention Is All You Need | NeurIPS 2017 | ✓ | ✓ | ✓ | ✓ |
| DiT | ICCV 2023 | ✓ | ✗ year | ✓ | ✓ |
| StreamingLLM | ICLR 2024 | ✗ arXiv | ✗ arXiv | ✓ | ✓ |
| UP-VLA | ICML 2025 | ✗ arXiv | ✗ arXiv | ✓ | ✓ |
| Sliding Windows Are Not the End | ACL 2025 | ✓ | ✗ arXiv | ✓ | ✓ |
| FLOWER | CoRL 2025 | ✗ arXiv | ✗ arXiv | ✓ | ✗ arXiv |

```
$ bibtools fetch ARXIV:2106.09685   # LoRA
Source: dblp | Venue: ICLR | Year: 2022
```

→ [Full comparison](comparison.md)

## What it does

1. **fetch** - Get bibtex from paper ID (arXiv, DOI, etc.)
2. **search** - Search papers by title and generate bibtex (use with caution)
3. **resolve** - Add `% paper_id:` comments to a .bib file (auto-match + confidence)
4. **verify** - Verify existing .bib entries (no modifications)
5. **review** - Interactively apply fixes for mismatches

## How it works

### Resolve

```
bibtools resolve main.bib
        ↓
If % paper_id exists → skip
Else:
  doi field → DOI:... (confidence 1.00)
  eprint field → ARXIV:... (confidence 1.00)
  title search → best match (confidence = title similarity)
        ↓
Write % paper_id comment
```

### Verify

```
bibtools verify main.bib
        ↓
Use % paper_id comments only
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

### Review

```
bibtools review main.bib
        ↓
Run verify
        ↓
Show mismatches and prompt per-field fixes
        ↓
Write updated .bib
```

**Data sources (Single Source of Truth):**

| Condition | Source |
|-----------|--------|
| DOI exists | **CrossRef** |
| No DOI, venue != arXiv | **DBLP** |
| No DOI, venue == arXiv | **arXiv** |

Semantic Scholar is used for identifier resolution only, not as a metadata source.

## Is it reliable?

bibtools does **NOT generate or guess metadata**.
It fetches data from official sources only:
- **CrossRef**: Official DOI registry with publisher-submitted metadata.
- **DBLP**: Computer science bibliography, used for venues without DOI (e.g., ICLR).
- **arXiv**: Used for preprints.

Semantic Scholar is used only for identifier resolution, not as a metadata source.

→ [Comparison with Google Scholar/Official sources](comparison.md)

---

## Installation

```bash
uv tool install git+https://github.com/MilkClouds/bibtools
```

## Quick Start

```bash
bibtools fetch 2106.09685                  # LoRA - auto-detects arXiv ID, gets ICLR 2022 from DBLP
bibtools resolve main.bib                   # Add % paper_id comments (auto-match + confidence in stdout)
bibtools verify main.bib                    # Verify existing entries (no modifications)
bibtools review main.bib                    # Interactive fix for mismatches
bibtools search "Attention Is All You Need"  # Search (use with caution)
```

## Commands

### resolve

Add `% paper_id:` comments to entries by ID fields or title matching.

```bash
bibtools resolve main.bib
bibtools resolve main.bib --min-confidence 0.90
bibtools resolve main.bib --dry-run
```

### verify

Verifies bibtex entries against official metadata from CrossRef/DBLP/arXiv. **Does not modify files.**

```bash
bibtools verify main.bib
bibtools verify main.bib --reverify
```

### review

Interactively fix mismatches detected by `verify`.

```bash
bibtools review main.bib
bibtools review main.bib --include-warnings
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

## Verification Strictness

bibtools is **strict by design** — it rejects abbreviations and ambiguous matches:

| Case | Result | Reason |
|------|--------|--------|
| `Smith, John` vs `John Smith` | ✓ PASS | Format difference only |
| `{GPT}` vs `GPT` | ⚠ WARNING | LaTeX braces difference |
| `M. Posner` vs `Michael Posner` | ✗ FAIL | Abbreviation = content change |
| `NeurIPS` vs `Neural Information Processing Systems` | ⚠ WARNING | Known alias |

→ [Full verification rules](FAQ.md#field-comparison-rules)

## Supported Paper IDs

- `ARXIV:2106.15928`
- `DOI:10.18653/v1/N18-3011`
- `CorpusId:215416146`
- `ACL:W12-3903`
- `PMID:19872477`

## More Information

→ [FAQ & Troubleshooting](FAQ.md) — Limitations, verification behavior, options reference

## Related Projects

- [**rebiber**](https://github.com/yuchenlin/rebiber) — A tool for normalizing bibtex with official info (DBLP, ACL anthology).
- [**SimBiber**](https://github.com/MLNLP-World/SimBiber) — A tool for simplifying bibtex with official info.

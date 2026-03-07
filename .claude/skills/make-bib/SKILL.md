---
name: make-bib
description: Generate accurate BibTeX for a paper
---

# make-bib

$ARGUMENTS — `arxiv:ID`, `doi:ID`, title in quotes, or abbreviation

For deeper background on source characteristics, see `${CLAUDE_SKILL_DIR}/citation-guide.md`.

## Rules

### Hard rules

- **Entry type**: conference/workshop → `@inproceedings`. Journal → `@article`. Preprint → per `[arxiv].entry_type`.
- **Workshop disclosure**: booktitle must contain "Workshop". Using only the parent conference name is misrepresentation.
- **Single source of truth**: all fields in one entry come from the same source. Never mix.
- **Honest status**: never cite a preprint as published or vice versa.
- **Discovery ≠ citation**: S2 and Google Scholar metadata are never used in BibTeX fields.

### Guidance

- **Source priority**: publisher/anthology > curated DB > preprint server. Customizable in `[sources].bibtex`.
- **Publication check**: S2 is a starting point only. Confirm via curated DB (CS: DBLP), review platform (OpenReview), or publisher page.
- **Provenance**: every entry gets a `% source:` annotation. Lower-confidence sources (CrossRef, manual) add `— verify fields`.

## Tools

`uv run ${CLAUDE_SKILL_DIR}/scripts/paper_sources.py`:
- `fetch <id>` — ID-based fetch from all sources. `--json` for structured output.
- `search <source> "<title>"` — title search (dblp, crossref, arxiv, openreview, s2).

`uv run ${CLAUDE_SKILL_DIR}/scripts/dblp_local.py`:
- `sync` — download/update local DBLP database.
- `search "<title>"` — search local DB by exact normalized title.

Direct BibTeX URLs (via WebFetch or curl):
- **DBLP**: `https://dblp.org/rec/{key}.bib`
- **ACL Anthology**: `https://aclanthology.org/{id}.bib`
- **PMLR**: `https://proceedings.mlr.press/v{volume}/{key}.html` — BibTeX embedded in page (covers ICML, AISTATS, CoRL, COLT, ALT, UAI, etc.)

Use `AskUserQuestion` when multiple candidates exist or venue is ambiguous.

## Workflow

### 1. Find the paper

Non-paper input (software, dataset, book) → `AskUserQuestion` for citation format. Stop.

ID input → `fetch`. Title/abbreviation → `search s2` → get IDs → `fetch`.

### 2. Determine publication status

`fetch --json <ID>` for S2 venue and external IDs (DOI, DBLP key, ACL ID, arXiv ID).

Confirm using `[sources].verify` in order:
- **Curated DB** (CS: `search dblp "<exact title>"`) — if listed, formally published.
- **Review platform** (`search openreview "<exact title>"`) — confirms acceptance. Check `invitation` for "Workshop" vs main track.
- **Publisher page** — presence in ACL Anthology, ACM DL, PMLR, etc. is definitive.
  - PMLR conferences (ICML, AISTATS, CoRL, COLT, UAI, ALT): search `proceedings.mlr.press` for the paper.

No venue confirmed → arXiv preprint.

### 3. Get BibTeX

Follow `[sources].bibtex` priority. Use the first source that has data.

Default CS lookup:

| Source | When | How |
|--------|------|-----|
| **ACL Anthology** | DOI prefix `10.18653/` | `https://aclanthology.org/{id}.bib` |
| **PMLR** | PMLR conference (ICML, CoRL, AISTATS, COLT, UAI, ALT) | WebFetch `https://proceedings.mlr.press/v{volume}/{key}.html` → extract BibTeX |
| **DBLP** | DBLP key exists | `https://dblp.org/rec/{key}.bib` (also searched via local DB by title) |
| **CrossRef** | DOI, no source above | Construct: `title`→title, `author[].family/given`→author, `container-title`→journal/booktitle, `published.date-parts`→year |
| **arXiv** | No formal venue | Construct `@article` per `[arxiv]` settings |

### 4. Validate, format, and output

Check hard rules. Apply `bibstyle.toml`:
- **Key**: per `[key].style` — `lastname_year` (`vaswani2017`), `lastname_venue_year` (`vaswani_neurips2017`), `acl` (`devlin-etal-2019-bert`)
- **Venue**: per `[venue].style` — `abbreviated` or `full`; `proceedings_prefix` adds "Proceedings of"
- **Authors**: truncate after `[authors].max` with `and others` (0 = no limit)
- **Fields**: include only those in `[fields]` for the entry type

Annotate above every entry with provenance and trust:
```
% source: dblp:conf/cvpr/HeZRS16 via dblp
% source: doi:10.xxx via crossref — verify fields
```

Output the annotated BibTeX entry only.

## `bibstyle.toml` schema

```toml
[sources]
# Sources to check publication status (checked in order)
verify = ["s2", "dblp", "openreview"]
# Sources to get BibTeX from (tried in priority order, highest first)
bibtex = ["acl_anthology", "pmlr", "dblp", "crossref", "arxiv"]
# Available: acl_anthology, pmlr, dblp, openreview, crossref, arxiv, inspire_hep, ads, pubmed

[fields]
conference = ["title", "author", "booktitle", "year"]
journal = ["title", "author", "journal", "year", "volume", "number"]
# Optional: "pages", "doi", "url", "publisher", "address", "editor", "month"

[authors]
max = 0  # 0 = unlimited

[venue]
style = "abbreviated"       # "abbreviated" or "full"
proceedings_prefix = false   # true: "Proceedings of NeurIPS"

[key]
style = "lastname_year"     # "lastname_year", "lastname_venue_year", "acl"

[arxiv]
entry_type = "article"                      # "article" or "misc"
journal_format = "arXiv preprint arXiv:{id}" # or "CoRR"
```

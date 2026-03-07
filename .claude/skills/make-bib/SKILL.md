---
name: make-bib
description: Generate accurate BibTeX for a paper
---

# make-bib

$ARGUMENTS — `arxiv:ID`, `doi:ID`, title in quotes, or abbreviation

For deeper background on source characteristics, see `${CLAUDE_SKILL_DIR}/citation-guide.md`.

## Rules

- **When in doubt, ask**: citation involves judgment calls the user should make. Use `AskUserQuestion` whenever the right choice isn't clear — multiple candidates for the same title, ambiguous venue, workshop vs main track, conflicting metadata across sources. Silent guessing risks misrepresentation.
- **Single source of truth**: all fields in one entry come from the same source. Never mix.
- **Honest representation**: never cite a preprint as published or vice versa. Workshop papers must have "Workshop" in booktitle — using only the parent conference name is misrepresentation.
- **Discovery ≠ citation**: tools that help find papers (S2, Google Scholar, etc.) optimize for coverage, not metadata accuracy. Use them for discovery and ID collection, but never copy their venue names, author formatting, or dates into BibTeX fields.
- **Entry type**: conference/workshop → `@inproceedings`. Journal → `@article`. Preprint → per `[arxiv].entry_type`.

## Tools

`uv run ${CLAUDE_SKILL_DIR}/scripts/paper_sources.py`:
- `fetch <id>` — ID-based fetch from all sources. `--json` for structured output.
- `search <source> "<title>"` — title search (dblp, crossref, arxiv, openreview, s2).

`uv run ${CLAUDE_SKILL_DIR}/scripts/dblp_local.py`:
- `sync` — download/update local DBLP database.
- `search "<title>"` — search local DB by normalized title.

## Workflow

### 1. Find the paper

**Goal**: identify the paper and collect external IDs (DOI, arXiv, DBLP key, ACL ID).

Non-paper input (software, dataset, book) → `AskUserQuestion` for citation format. Stop.

ID input → `fetch`. Title/abbreviation → `search s2` → get IDs → `fetch`.

S2 is useful here for discovery — broad coverage, returns external IDs quickly. But S2 metadata (venue names, dates) is unreliable and must not carry over to later steps.

### 2. Determine publication status

**Goal**: know whether the paper is formally published, and at which venue — or whether it remains a preprint.

`fetch --json <ID>` returns S2 venue hints and external IDs. These hints need confirmation from more authoritative sources:

- **Curated DB** (CS: `search dblp "<exact title>"`) — if DBLP lists it under a venue, it's formally published there.
- **Review platform** (`search openreview "<exact title>"`) — confirms acceptance decisions directly. Check `invitation` field to distinguish workshop from main track.
- **Publisher page** — presence in ACL Anthology, ACM DL, PMLR, etc. is definitive.

No venue confirmed → treat as arXiv preprint.

The `[sources].verify` list in `bibstyle.toml` controls which checks run and in what order.

### 3. Get BibTeX

**Goal**: obtain citation data from the most authoritative source available.

Higher-authority sources produce more reliable, complete BibTeX. The hierarchy reflects trustworthiness, not a rigid sequence — use the best source you can reach:

**Tier 1 — Publisher / Anthology** (authoritative metadata direct from publisher):

| Source | URL | Scope |
|--------|-----|-------|
| ACL Anthology | `https://aclanthology.org/{id}.bib` | DOI prefix `10.18653/` |
| PMLR | `https://proceedings.mlr.press/v{vol}/{key}.html` | ICML, AISTATS, CoRL, COLT, UAI, ALT |
| arXiv | `https://arxiv.org/abs/{id}` | Preprint (no formal venue confirmed in step 2). Construct `@article` per `[arxiv]` settings |
| Other publishers | ACM DL, IEEE Xplore, Springer, etc. | Any venue with official proceedings page |

**Tier 2 — Curated DB** (normalized, reliable for CS):

| Source | URL | Scope |
|--------|-----|-------|
| DBLP | `https://dblp.org/rec/{key}.bib` | By key, by title (local DB), or by DOI (`dblp.org/doi/{doi}.bib`) |
| Others by field | INSPIRE-HEP (physics), ADS (astronomy), PubMed (medicine), etc. | See `[sources]` in bibstyle.toml |

**Tier 3 — Fallback** (constructed from API data — requires `⚠ UNVERIFIED` annotation):

| Source | Provenance URL | Scope |
|--------|---------------|-------|
| CrossRef | `https://doi.org/{doi}` | DOI exists, no higher-tier source. Construct from API JSON |
| OpenReview | `https://openreview.net/forum?id={id}` | Recent acceptances or workshops not yet in Tier 1–2. Auto-generated BibTeX — verify venue name and fields |

Constructing from CrossRef: `title`→title, `author[].family/given`→author, `container-title`→journal/booktitle, `published.date-parts`→year.

The `[sources].bibtex` list in `bibstyle.toml` controls priority order.

### 4. Validate, format, and output

**Goal**: a correct, consistently formatted entry with clear provenance.

Check rules. Apply `bibstyle.toml`:
- **Key**: per `[key].style` — `lastname_year` (`vaswani2017`), `lastname_venue_year` (`vaswani_neurips2017`), `acl` (`devlin-etal-2019-bert`)
- **Venue**: per `[venue].style` — `abbreviated` or `full`; `proceedings_prefix` adds "Proceedings of"
- **Authors**: truncate after `[authors].max` with `and others` (0 = no limit)
- **Fields**: include only those in `[fields]` for the entry type

Annotate with provenance. Tier 1–2 get a source line; Tier 3 gets an additional warning:
```
% source: dblp:conf/cvpr/HeZRS16 via dblp (https://dblp.org/rec/conf/cvpr/HeZRS16.bib)

% ⚠ UNVERIFIED — constructed from API data, not from authoritative source
% source: doi:10.xxx via crossref (https://doi.org/10.xxx)
```

Output the annotated BibTeX entry only.

## `bibstyle.toml` schema

```toml
[sources]
# Discovery & verification: checked to determine publication status
verify = ["s2", "dblp", "openreview"]
# BibTeX citation: tried in priority order (Tier 1 → Tier 3)
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

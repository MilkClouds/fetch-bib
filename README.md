# make-bib: All you need is the final look

A [Claude Code skill](https://code.claude.com/docs/en/skills) that generates BibTeX from authoritative sources.

**It does:** Fetches BibTeX from the publisher first (ACL Anthology, PMLR, arXiv), falls back to curated databases (DBLP), formats the entry, and always shows exactly where each entry came from. The mechanical half of citation, handled.

**It does not:**
- **Guess.** The first rule is **when in doubt, ask.** Multiple candidates, ambiguous venue, workshop vs main track — it stops and asks you.
- **Generate.** Every field comes from an [authoritative source](#sources) — not from an LLM filling in blanks.

```
> /make-bib StreamingLLM

% source: dblp:conf/iclr/XiaoTCHL24 via dblp
@inproceedings{xiao2024streamingllm,
  author    = {Guangxuan Xiao and Yuandong Tian and Beidi Chen
               and Song Han and Mike Lewis},
  title     = {Efficient Streaming Language Models
               with Attention Sinks},
  booktitle = {ICLR},
  year      = {2024},
}
```

Google Scholar would give you arXiv 2023 for this paper. It's ICLR 2024.

When something is ambiguous, it stops and asks:

```
> /make-bib "Scaling Data-Constrained Language Models"

? This paper appears in two venues:
  1. NeurIPS 2023 (main conference)
  2. NeurIPS 2023 Workshop on Instruction Tuning
  Which version are you citing?

> 1

% source: dblp:conf/neurips/MuennighoffRWS23 via dblp
@inproceedings{muennighoff2023scaling,
  author    = {Niklas Muennighoff and Alexander M. Rush
               and Boaz Barak and Teven Le Scao
               and Aleksandra Piktus and Nouamane Tazi
               and Sampo Pyysalo and Thomas Wolf
               and Colin Raffel},
  title     = {Scaling Data-Constrained Language Models},
  booktitle = {NeurIPS},
  year      = {2023},
}
```

## Sources

**Tier 1 — Publisher / Anthology** (authoritative metadata direct from publisher):

| Source | Scope |
|---|---|
| ACL Anthology | ACL, EMNLP, NAACL, and NLP workshops |
| PMLR | ICML, AISTATS, COLT, UAI, CoRL, ALT |
| arXiv | Preprints (when no formal venue is confirmed) |

**Tier 2 — Curated DB** (normalized, reliable):

| Source | Scope |
|---|---|
| DBLP | ~40 CS conferences via local database (includes IEEE, ACM venues) |

**Tier 3 — Fallback:**

| Source | Scope |
|---|---|
| CrossRef | Any paper with a DOI, when higher tiers unavailable |
| OpenReview | Recent acceptances or workshops not yet in Tier 1–2 |

Entries from Tier 3 sources are labeled `⚠ UNVERIFIED` in the output. If you see this marker, verify the venue name, author list, and year yourself before using the entry.

## Workflow

```
Input: paper ID, title, or abbreviation
         │
         ▼
    ┌─ Resolve ──────────────────────────────┐
    │  Semantic Scholar → external IDs        │
    │  (DOI, DBLP key, ACL ID, arXiv ID)     │
    └────────────────────────┬───────────────┘
                             │
         ┌─ Verify status ───┤
         │  DBLP / OpenReview / publisher page │
         │  → published or preprint?           │
         └───────────────────┬────────────────┘
                             │
         ┌─ Fetch BibTeX ────┤               ambiguous?
         │  Tier 1: Publisher, arXiv       ──────→ asks you
         │  Tier 2: DBLP                       (multiple candidates,
         │  Tier 3: CrossRef, OpenReview        workshop vs main,
         └───────────────────┬────────────────┘ venue unclear)
                             │
         ┌─ Format ──────────┤
         │  Apply bibstyle.toml                │
         │  (key, venue, fields, authors)      │
         └───────────────────┬────────────────┘
                             │
                             ▼
                        You review.
```

## Usage

```
> /make-bib arxiv:2106.09685
> /make-bib doi:10.1109/CVPR.2016.90
> /make-bib "Attention Is All You Need"
> /make-bib LoRA
```

## Configuration

Create `bibstyle.toml` in your project root:

```toml
[sources]
verify = ["s2", "dblp", "openreview"]
bibtex = ["acl_anthology", "pmlr", "dblp", "crossref", "arxiv"]

[fields]
conference = ["title", "author", "booktitle", "year"]
journal = ["title", "author", "journal", "year", "volume", "number"]

[venue]
style = "abbreviated"       # or "full"
proceedings_prefix = false   # true → "Proceedings of NeurIPS"

[key]
style = "lastname_year"     # "lastname_year", "lastname_venue_year", "acl"

[arxiv]
entry_type = "article"
journal_format = "arXiv preprint arXiv:{id}"
```

## Local DBLP database

Bundled local database covers ~40 CS conferences (2000–2026) for instant title-based lookup without hitting the DBLP API. Inspired by [rebiber](https://github.com/yuchenlin/rebiber).

```bash
uv run scripts/dblp_local.py sync                    # update all
uv run scripts/dblp_local.py sync -c neurips -y 2024  # specific venue/year
uv run scripts/dblp_local.py stats                    # show coverage
```

## Design rationale

No prominent researcher has published a guide on citation management — because it's a craft skill, not an algorithm. The universal pattern is: copy from an authoritative source, manually verify, apply conventions consistently. make-bib automates steps 1 and 3. Step 2 is yours.

## Related projects

- [**rebiber**](https://github.com/yuchenlin/rebiber) — Normalizes arXiv BibTeX with DBLP/ACL data. make-bib's local database is inspired by rebiber's approach.
- [**SimBiber**](https://github.com/MLNLP-World/SimBiber) — Simplifies BibTeX to minimal fields.

# make-bib: All you need is the final look

A [Claude Code skill](https://code.claude.com/docs/en/skills) that generates BibTeX from authoritative sources.

**It does:** Fetches BibTeX from the publisher first (ACL Anthology, PMLR, arXiv), falls back to curated databases (DBLP), formats the entry, and always shows exactly where each entry came from. The mechanical half of citation, handled.

**It does not:**
- **Guess.** The first rule is **When in doubt, ask.** Multiple candidates, ambiguous venue, workshop vs main track — it stops and asks you.
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
> /make-bib Scaling Laws

? Which "Scaling Laws" paper do you want cited?
  1. Kaplan et al. 2020 — Scaling Laws for Neural Language Models (arXiv:2001.08361)
  2. Cherti et al. 2023 — Reproducible Scaling Laws for Contrastive Language-Image Learning (CVPR 2023)
  3. Lin et al. 2024 — Data Scaling Laws in Imitation Learning for Robotic Manipulation (ICLR 2025)

> 3

% source: dblp:conf/iclr/LinHSWY025 via dblp
@inproceedings{lin2025data,
  title     = {Data Scaling Laws in Imitation Learning
               for Robotic Manipulation},
  author    = {Fanqi Lin and Yingdong Hu and Pingyue Sheng
               and Chuan Wen and Jiacheng You and Yang Gao},
  booktitle = {ICLR},
  year      = {2025},
}
```

## Limitations

make-bib is an LLM skill. It fetches from authoritative sources and follows rules, but it can still pick the wrong source, misformat fields, or hallucinate under edge cases. Always review the output before citing.

Designed for and tested with Claude Opus 4.6. Correct behavior with lower-tier models (Sonnet, Haiku) is not guaranteed.

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
- [**bibtex-dblp**](https://github.com/volkm/bibtex-dblp) — Python tool to retrieve BibTeX entries from DBLP.
- [**Generating BibTeX from DOIs via DBLP**](https://www.joachim-breitner.de/blog/806-Generating_bibtex_bibliographies_from_DOIs_via_DBLP) — Blog post on using DBLP as a DOI-to-BibTeX resolver.

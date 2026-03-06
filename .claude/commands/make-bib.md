# make-bib: Generate clean BibTeX for a paper

$ARGUMENTS — `arxiv:ID`, `doi:ID`, `openreview:ID`, or title in quotes

## Steps

1. **Fetch metadata** using `paper_sources.py`.
   - ID input: `uv run paper_sources.py fetch --json <paper_id>`
   - Title input: `uv run paper_sources.py search s2 -t "<title>" --json` to find the paper, then fetch.
   - Use `search` and `fetch` subcommands flexibly as needed — e.g. search specific sources, fetch with `--sources`, re-search if initial results are insufficient.

2. **Generate BibTeX** from the aggregated data, applying these conventions. When sources conflict or data is ambiguous, use `AskUserQuestion` (2–4 options with `label` + `description`) — never silently pick one side.

   **Venue precedence** (default): Journal > Conference > Workshop > arXiv

   **Entry type & fields**:
   - Conference → `@inproceedings{key, title, author, booktitle, year}` — no pages/editors/publishers/doi
   - Journal/arXiv → `@article{key, title, author, journal, year, volume, number}`
   - arXiv preprint: `journal={arXiv preprint arXiv:XXXX.XXXXX}`

   **Formatting**:
   - Abbreviate well-known venues (`NeurIPS`, `ICML`, etc.). If unsure, ask.
   - Protect proper nouns/acronyms in titles: `{BERT}`, `{ImageNet}`, `{B}ayesian` — don't over-brace.
   - Authors: `Last, First and Last, First`. Remove DBLP disambiguation numbers.
   - Key: `lastname2024`. Prefer ACL Anthology key if available.
   - Title source priority: DBLP > arXiv > CrossRef. Strip trailing periods.

   **Authoritative sources**: ACL Anthology BibTeX for ACL venues. OpenReview `_bibtex` is useful but verify.

3. Output ONLY the BibTeX entry.

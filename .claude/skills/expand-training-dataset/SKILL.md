---
name: expand-training-dataset
description: >-
  Efficiently expand a labeled ML training dataset (any task: span
  labeling, classification, extraction) inside this project by mining
  adjacent real data sources already sitting in the repo, before reaching
  for synthetic generation or slow manual annotation. Use this whenever a
  training corpus has known category/class support gaps against a
  readiness gate (e.g. G1-G5 in prepare_privacy_filter_dataset.py),
  someone asks "can we use data we already have" / "how do we get more
  gold", or a dataset needs scaling and the project has other scrapers/
  archives (tjro_juris, stj_acordaos, djen_backup, ...) that might cover
  the same document types under a different collection pipeline. Not for
  generating wholly synthetic examples (see RFC 0011 /
  scripts/synthetic_segmenter/ for that) — this skill is specifically
  about extracting MORE REAL labeled examples cheaply from data the
  project already has.
---

## Core idea

Before generating more synthetic data or manually annotating from
scratch, check whether an **adjacent real data source already collected
in this repo** can supply real examples for the categories that are
short — especially when that source has a **structural self-labeling
property**: a document whose *entire* content already corresponds to one
target category (its own source-system classification says so), so the
label anchors sit at the known start/end of the document instead of being
buried somewhere inside a much longer combined document.

This was discovered concretely for the decision-segmenter task: TJRO's
JURIS system (`src/tjro_juris`, ~2.45M documents already scraped to
Internet Archive) classifies each document by `tipo` — a `VOTO`-tipo
document's whole text *is* a voto, an `EMENTA`-tipo document's whole text
*is* an ementa. That turned "find `voto_inicio`/`voto_fim` anchors buried
inside a multi-page caderno" into "match a known phrase at the start and
end of a short, already-typed document" — orders of magnitude cheaper
than manual annotation, and orders of magnitude more data than the
scarce categories needed.

## Workflow

### 1. Quantify the actual gap — don't guess

Compute real per-category support against the project's own gate/
threshold (e.g. `_GATE_MIN_TRAIN_SUPPORT` in
`scripts/prepare_privacy_filter_dataset.py`). Know exactly which
categories are short and by how much before looking for more data — this
tells you what "enough" looks like and stops you from over-collecting.

### 2. Survey adjacent sources already in the repo

Look for other scrapers/archives/manifests (`src/*_juris`,
`src/stj_acordaos`, `src/djen_backup`, `data/*/manifest.*`) that might
cover the same real-world document types through a *different* collection
pipeline than the one the current gold came from. A different pipeline
often means cleaner text (no OCR), different metadata, or — critically —
a classification field that already tells you what's inside a document.

### 3. Pull a small, diverse sample first — never scale up blind

Download a handful of files across different time periods/sources (not
just the most recent one — conventions and phrasing drift over years).
Inspect actual document heads/tails by hand before writing any extraction
code. Look specifically for:
- A category whose entire document content matches one target label
  (whole-document-is-the-span shortcut).
- What phrase sits at the natural start/end of that content.
- **Multiple regimes** — real corpora are not monolithic. TJRO's data
  had two closing conventions for the same category (regular chambers vs.
  Juizados Especiais under Lei 9.099/95) that would have been silently
  missed by testing against only one era/court branch.

### 4. Build a narrow, mechanically-validated extractor

- Match known anchor phrases (from the project's existing phrase bank if
  one exists) at the document's structural boundary — don't hunt for
  anchors mid-document with this technique; that's a different, harder
  problem.
- Run every candidate through the project's existing offset/invariant
  validators (e.g. `transform.check_final_invariants`) — never hand-roll
  a second offset-correctness check.
- A missing closing anchor is not necessarily a rejection — check whether
  the label schema already has a "no closing cue, extends to EOD" case
  (most guideline-driven span schemas do) and use it instead of discarding
  usable examples.
- Reject on: too-short text, and residual noise from the source system
  (encoding artifacts, leftover Word/OpenXML metadata, etc.) — but detect
  noise **across the whole text**, not just one end of it.

### 5. Audit a small sample yourself before trusting the output

Mechanical validation only proves offset bookkeeping is correct — it says
nothing about whether the phrase-matching itself is *complete* or
*correct*. Before scaling up or touching real gold:

- Sample a **stratified** set — a few records from every `(source_type,
  matched/unmatched)` bucket, not just the top N or a random flat sample.
  Bugs hide in the edges (unmatched cases, rare types), not the bulk.
- Read each one's actual labeled spans (`text[start:end]`), plus the
  surrounding head/tail, by hand.
- Look specifically for: noise that slipped past the filter, a stable
  anchor phrase that got over-specified with a variable lead-in/context
  clause (making it too brittle to match real variation), and common real
  phrasings/abbreviations the pattern list doesn't have yet.

### 6. Fix findings narrowly, re-verify with evidence

When the audit finds a real bug, fix it grounded in what was actually
observed in the sample — don't invent new phrase variants speculatively.
Then:
- Re-run the extractor and compare before/after counts.
- Spot-check specifically the **newly-affected** records (the delta), not
  just the aggregate numbers — a count going up doesn't prove the new
  matches are correct.
- Add a regression test per real bug found, quoting the actual problem
  text that exposed it.

### 7. Keep candidates separate from verified gold

Heuristically-extracted records are **candidates**, not gold, even after
passing mechanical validation and a spot-check audit. Write them to a
separate candidates file; never let an extractor script write directly
into the project's canonical training file. Match whatever
verification convention the existing gold went through (e.g. this
project's `data/segmenter_splits/manifest.json` documents a
"prompt_subagents:haiku" labeling + verification pass) before merging.

### 8. Feed real findings back into shared resources

New phrase variants, patterns, or noise signatures found during the audit
belong in the project's shared phrase bank/pattern library (e.g.
`scripts/synthetic_segmenter/phrase_banks.py`), with a comment citing
that they were found in a real sample — this makes every later user of
that resource (including synthetic generators) benefit from the same
grounding.

## When NOT to use this

- The gap category has no plausible adjacent real source (e.g.
  `preliminar_*`/`acordao_decisorio_*` in the segmenter task — no JURIS
  `tipo` corresponds to those; extraction would need to search *inside*
  full documents, a fundamentally different, harder problem than
  whole-document self-labeling).
- You need deliberately rare, controlled, or adversarial examples (hard
  negatives, edge-case combinations) — that's what synthetic generation
  (`scripts/synthetic_segmenter/`) is for, not real-corpus mining.
- The "gap" hasn't been quantified yet — go compute it against the real
  gate first (step 1); don't start extracting before you know the target.

## Worked example (reference implementation)

`scripts/juris_extract_gold_candidates.py` + the `phrase_banks.py`
expansion in the same commit series is a complete, tested worked example
of this whole workflow for the decision-segmenter task: gap quantified
via the G2 gate, `tjro_juris` surveyed as the adjacent source, a 10-file/
~31k-row real sample pulled and inspected, a narrow extractor built and
validated, a manual stratified 20-record audit run, 3 real bugs found and
fixed (noise-filter blind spot, over-brittle anchor, missed real
abbreviation), and every fix re-verified against the real delta before
being trusted. Read that commit history for the concrete before/after
numbers and audit transcript.

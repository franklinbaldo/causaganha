---
name: expand-training-dataset
description: >-
  Efficiently expand a labeled ML training dataset (any task: span
  labeling, classification, extraction) inside this project by mining
  adjacent real data sources already sitting in the repo, before reaching
  for synthetic generation or slow manual annotation. Covers both
  mechanical whole-document self-labeling AND pre-filter + one-subagent-
  per-document labeling for categories buried inside larger documents
  (e.g. preliminar_*, custas/honorarios) that self-labeling can't reach.
  Use this whenever a training corpus has known category/class support
  gaps against a readiness gate (e.g. G1-G5 in
  prepare_privacy_filter_dataset.py), someone asks "can we use data we
  already have" / "how do we get more gold", or a dataset needs scaling
  and the project has other scrapers/archives (tjro_juris, stj_acordaos,
  djen_backup, ...) that might cover the same document types under a
  different collection pipeline. Not for generating wholly synthetic
  examples (see RFC 0011 / scripts/synthetic_segmenter/ for that) — this
  skill is specifically about extracting MORE REAL labeled examples
  cheaply from data the project already has.
---

## Core idea

Before generating more synthetic data or manually annotating from
scratch, check whether an **adjacent real data source already collected
in this repo** can supply real examples for the categories that are
short. Two techniques, cheapest first:

1. **Structural self-labeling** (steps 1-8) — the source has a document
   whose *entire* content already corresponds to one target category (its
   own source-system classification says so), so label anchors sit at the
   known start/end of the document instead of being buried inside a much
   longer combined document. Fully mechanical, no per-document human/LLM
   judgment needed.
2. **Pre-filter + subagent labeling** (step 9) — when the category sits
   *inside* a larger document with no self-labeling shortcut, a cheap
   textual pre-filter can still concentrate a small batch on documents
   that plausibly contain it, then one subagent per document does the
   actual labeling. More expensive than (1) but still far cheaper than
   sampling blind, and it works on categories (1) cannot reach at all.

Technique (1) was discovered concretely for the decision-segmenter task:
TJRO's JURIS system (`src/tjro_juris`, ~2.45M documents already scraped
to Internet Archive) classifies each document by `tipo` — a `VOTO`-tipo
document's whole text *is* a voto, an `EMENTA`-tipo document's whole text
*is* an ementa. That turned "find `voto_inicio`/`voto_fim` anchors buried
inside a multi-page caderno" into "match a known phrase at the start and
end of a short, already-typed document" — orders of magnitude cheaper
than manual annotation, and orders of magnitude more data than the
scarce categories needed. Technique (2) later closed categories (1)
couldn't reach at all — see step 9.

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

### 9. When whole-document self-labeling doesn't apply: pre-filter + subagent labeling

Some categories genuinely have no `tipo` that self-labels them — they sit
*inside* a larger document (e.g. `preliminar_*`, `custas_fim`/
`honorarios_fim`, `fundamentacao_legal` in the segmenter task). Step 4's
mechanical extraction doesn't apply, but that doesn't mean the source
is unusable — it means the pre-filter and the labeling step both change:

- **Pre-filter on a cheap, high-precision textual signal**, even an
  imperfect one, to concentrate a small labeling batch on documents that
  actually contain the target category, instead of sampling blind and
  hoping. A literal regex on a structural heading (e.g. `\b1\.\s*
  PRELIMINARES?\b`) or on a pair of keyword substrings both mentioned
  together (e.g. documents containing both "custas" and "honorarios")
  works well — it doesn't need to resolve offsets, just narrow the
  candidate pool. **Verify the filter isn't accidentally sampling a
  narrow time slice or venue**: check hit rate across several years/
  sources before committing to one file, the way step 3 already warns for
  whole-document extraction — a heading convention can be genuinely
  recent (this project found a numbered-heading convention with zero
  hits in 2005/2008/2017 samples and 21 hits in one 2024 file alone).
- **Label with one subagent per document**, each independently briefed
  with the full annotation guideline, the doc-type framing, and — this
  matters — explicit anti-pattern warnings for the *specific* confusable
  pattern the pre-filter is likely to also surface (e.g. a dispositivo
  outcome-summary line that reuses the same keyword as the real heading:
  "PRELIMINAR REJEITADA. NO MÉRITO, RECURSO NÃO PROVIDO" is not a
  `preliminar_inicio`). Have each subagent report `{category, match, nth}`
  findings, never hand-counted offsets, and resolve through the project's
  existing `from-spans` tool the same way the original seed did.
- **Independent subagents can converge on the exact same span** when a
  category pair is genuinely fused in the real prose (see next point) —
  expect and mechanically resolve real `validate` overlap errors after
  merging a batch, don't treat them as a labeling failure to throw away.

### 10. A validator overlap error can be a real discovery, not just a bug

If `opf_annotate.py validate` (or your project's equivalent) reports
BIOES/offset overlap errors on a freshly-merged batch where every
individual subagent's output looked internally consistent, check whether
the categories in conflict are *actually* the same clause in real
prose before assuming a labeling mistake. This project found that
Juizado Especial sentenças overwhelmingly fuse `custas` and `honorarios`
into one sentence with no clean boundary ("Sem custas e honorários
advocatícios...") — independent subagents legitimately anchored both
categories on the identical span. Resolve deterministically (e.g. keep
the first-listed category per conflict, drop the duplicate) and log the
finding — it's real information about the category schema's fit to the
domain, and it should feed back into the label bank the same way any
other real-corpus finding does (step 8).

### 11. When a stratified — not random — split is required

If a newly-labeled batch is the *only* source for a weak category (or one
of very few), a random train/val/test split can leave val or test with
zero examples of it purely by chance, even though the gate needs every
split to clear its own minimum independently. Before splitting, tabulate
which documents carry which weak categories, then hand-pick val/test
membership to guarantee each split's minimum is met, and let train absorb
the remainder. Document the split as intentional (not random) in the
provenance manifest, including the doc/category tabulation that drove it
— a future reader needs to know the split wasn't randomized before they
draw conclusions from eval numbers on it.

### 12. Flag structural ambiguities the guideline hasn't settled yet — don't paper over them

Real documents sometimes contain a genuinely ambiguous case the
annotation guideline doesn't yet resolve — e.g. an acórdão's voto
transcribing a *complete* lower-court sentença verbatim (its own nested
relatório/preliminares/mérito/dispositivo), where reasonable labelers
will differ on whether to tag the nested structure. When multiple
subagents in the same batch make different defensible calls on the same
pattern, that's a real inconsistency now baked into gold, not noise to
average away. Note it explicitly in the batch's provenance manifest and
treat it as an open item for the guideline itself — don't let each future
batch re-litigate the same ambiguity independently and silently drift
further apart.

## When NOT to use this

- You need deliberately rare, controlled, or adversarial examples (hard
  negatives, edge-case combinations) — that's what synthetic generation
  (`scripts/synthetic_segmenter/`) is for, not real-corpus mining. (Note:
  a category having no *whole-document* self-labeling source, per step 4,
  is NOT the same as having no adjacent real source at all — see step 9;
  this project initially assumed `preliminar_*` needed synthetic-only
  treatment for exactly this reason, and that assumption turned out to be
  wrong once a pre-filter + subagent-labeling approach was tried.)
- The "gap" hasn't been quantified yet — go compute it against the real
  gate first (step 1); don't start extracting before you know the target.

## Worked examples (reference implementations)

**Technique 1 (self-labeling):** `scripts/juris_extract_gold_candidates.py`
+ the `phrase_banks.py` expansion in the same commit series — gap
quantified via the G2 gate, `tjro_juris` surveyed as the adjacent source,
a 10-file/~31k-row real sample pulled and inspected, a narrow extractor
built and validated, a manual stratified 20-record audit run, 3 real bugs
found and fixed (noise-filter blind spot, over-brittle anchor, missed
real abbreviation), and every fix re-verified against the real delta
before being trusted.

**Technique 2 (pre-filter + subagent labeling):** the two 20-document
"Round A"/"Round B" batches added to `data/segmenter_splits/` on
2026-07-16 (see that commit series and `manifest.json`'s `notes` field) —
Round A pre-filtered `tjro_juris` ACORDAO documents on a numbered
`1. PRELIMINARES` heading regex (confirmed real-but-recent via a
per-year hit-rate check, step 9) to close a zero-support gate technique 1
couldn't reach; Round B pre-filtered SENTENCA documents on co-occurring
"custas"/"honorarios" substrings to close three more categories,
surfaced the fused-clause discovery (step 10) via real `validate` overlap
errors, and used a hand-picked (step 11) rather than random val/test
split because the target categories only had 5-20 source documents to
draw from. Both batches' findings were fed back into
`scripts/synthetic_segmenter/phrase_banks.py` and `hard_negatives.py`
(step 8) the same day.

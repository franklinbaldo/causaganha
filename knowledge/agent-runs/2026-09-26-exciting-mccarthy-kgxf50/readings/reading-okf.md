---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-kgxf50-reading-okf"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
subject: "okf_knowledge"
reference: "docs/rfc/0012-segmenter-dataset-confiavel-baseline.md + knowledge/agent-runs/2026-09-26-exciting-mccarthy-{ku8qje,p08457,uz8msx}/run.md"
finding: "RFC 0012 Sec 5 item 4 sets a >=30/>=30 val/test floor on ACCEPTED reviews, not raw document count; the floor became reachable only after Lote 28 (round ku8qje) raised the corpus ceiling to 30/30. Round p08457 proved a repeatable per-round adjudication rate of ~2 documents via one Agent-tool subagent (haiku) per document, and left test_count at 4/30 with 141 eligible candidates and a mandatory simulate-before-annotate discipline."
---

# Reading: OKF knowledge — RFC 0012 + last 3 same-day run reports

Read `docs/rfc/0012-segmenter-dataset-confiavel-baseline.md` (the
governing spec for the segmenter dataset store, referenced by every
segmenter script's docstring) plus the full `run.md` of the three most
recent same-day `AgentRun` reports (`uz8msx`, `ku8qje`, `p08457`) to
understand exactly how this round should continue the work rather than
re-deriving the mechanism from scratch.

**RFC 0012 mechanics relevant to this round:**
- §5 item 4: model-selection experiments require >=30 val documents and
  >=30 test documents, each backed by an *accepted* `ReviewRecord`
  (`segmenter_dataset.splits.evaluation_eligible_document_ids`), not
  merely present in the corpus.
- §8/§9: a document becomes review-eligible once it has exactly two
  independent annotations (`seeded_with="none"` on both,
  `model_family` must differ between the two — independence is a
  property of the *pair*, enforced by
  `SegmenterDatasetStore.write_review`'s `NonIndependentReviewError`).
- §11: mechanical validation (`validate_record`) is a hard gate before
  any annotation or review can be written — verbatim-fidelity check
  (tag-stripped reproduction must equal the stored document byte-for-byte)
  plus span/overlap/category validation.
- `assign_splits` recomputes the *entire* val/test partition from a
  fixed hash of `(seed, group_id)` on every run — which single document
  lands in val vs. test is not directly controllable, only the
  aggregate `val_count`/`test_count` are a checkable contract. This is
  why every prior adjudication round **simulates** `assign_splits`
  (via `scripts/segmenter_governance_status.py`) before spending
  annotation effort on a specific candidate.

**Continuity from the last 3 same-day runs (all merged, all green):**
- `uz8msx` (this morning): pure tracker-integrity work (#950 reopening,
  closing 3 stale codex PRs, unstuck 2 merges) — no segmenter change,
  but its `next_move` explicitly named the segmenter track as "the most
  mature product work" with no PR in flight.
- `ku8qje` (PR #1666): grew the corpus (#1050, Lote 28) specifically
  because governance status showed the val/test ceiling stuck at
  29/29 — one document short of the RFC 0012 floor even at 100%
  adjudication. `document_count` 195->197 raised the ceiling to 30/30.
- `p08457` (PR #1668/#1669, the immediately preceding round): first
  round to *simulate* `assign_splits` per-candidate before selecting,
  adjudicated 2 documents (TRF6, TRF2) via genuinely independent
  `Agent`-tool subagents (`model=haiku`), found and fixed one real
  XML-nesting defect (not a content disagreement) before ingestion,
  TDD RED (`assert 32 >= 34`) -> GREEN. Left `test_count=4` of 30,
  `val_count=30` (already at ceiling — no more val-side work needed,
  every future adjudication should aim to land in the test split when
  simulated), 141 eligible candidates, 134 of which move `test_count`
  in isolation.

**What this reading rules out:** re-growing the corpus (#1050) is not
necessary this round — the ceiling is already at 30/30 and 141 eligible
candidates exist unadjudicated. The bottleneck is purely adjudication
throughput on #1051, which is what this round's goal targets.

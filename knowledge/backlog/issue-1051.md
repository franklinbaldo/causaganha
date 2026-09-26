---
type: BacklogItem
issue_number: 1051
title: "segmenter: build an independently annotated validation set for model selection"
category: "ml_data_work"
blocking_reason: "Not blocked. The mechanism is proven: scripts/annotate_second_independent.py (second independent annotation, model_family must differ from the first -- convention is prompt_subagents:haiku via Agent tool with model=haiku, vs the first annotation's prompt_subagents:general-purpose) + scripts/adjudicate_segmenter_review.py (reconcile into an accepted ReviewRecord) + scripts/segmenter_governance_status.py (real vs ceiling val/test counts, RFC 0012 Sec 5 item 4's >=30/>=30 floor)."
unblock_condition: "Already unblocked. Issue #1050 (Lote 28, round ku8qje) crossed the corpus-scale ceiling on 2026-09-26: with document_count=197, val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication both reached 30 for the first time -- the floor is reachable in principle. The remaining gap is pure adjudication coverage, concentrated on the TEST side: after PR #1670 (round kgxf50), review_count=37, val_count=30 (already at its ceiling), test_count=7 (of 30). A future round should keep picking single-annotated, unreviewed, seeded_with=='none' candidates (a document whose sole annotation has seeded_with != 'none' can NEVER be adjudicated -- filter for this before selecting) and SIMULATE assign_splits with each candidate added to evaluation_eligible (in isolation, then jointly with the round's full batch) BEFORE spending annotation effort -- assign_splits recomputes the whole val/test partition from a fixed hash order of (seed, group_id) every time it runs, so which specific document lands in val vs test isn't controllable by identity, only the aggregate test_count/val_count are the real, checkable contract. Roughly 23 more accepted reviews are needed on average to reach test_count>=30 (fewer if a lucky hash ordering front-loads test; simulate rather than assume)."
last_verified_run_id: "runs/20260926T062628Z-do-the-best-useful-work-available-in-this-reposi"
last_verified_at: "2026-09-26T06:45:00Z"
status: "unblocked"
---

# Issue #1051: segmenter: build an independently annotated validation set for model selection

Not blocked -- ready to keep scaling with the existing tooling. This is
the first `knowledge/backlog/issue-1051.md` (the issue opened
2026-09-16 with no dedicated backlog file until now; two earlier
rounds noted the gap but scoped it out).

**Round ns7mbo (PR #1665, 2026-09-25/26, Wisk loop):** first tracked
progress on #1051 since it opened. One accepted `ReviewRecord` for
`doc_003c99b9812d01848478f7ff0bf16238` (TJPA) via a genuinely
independent second annotation (`model_family=prompt_subagents:haiku`).
`review_count` 31->32, `test_count` 2->3 (of a 29/29 ceiling itself
below the RFC 0012 floor at the time). Two earlier attempts to
adjudicate a second document
(`doc_82d8ee7168b24d787ce0417f888d1eb3`, TJPB) both failed
mechanical/verbatim verification before ingestion and were correctly
rejected, never written to the store.

**Round ku8qje (PR #1666, 2026-09-26):** grew the corpus instead
(issue #1050, Lote 28) because a live `segmenter_governance_status.py`
check showed the val/test ceiling at 29/29 -- one document short of
the RFC 0012 floor even at 100% adjudication of the existing pool.
`document_count` 195->197 pushed the ceiling to 30/30 for the first
time, unblocking #1051's remaining work as a pure coverage gap.

**Round p08457 (this round, 2026-09-26):** adjudicated 2 more
documents, chosen by live simulation (not guesswork) of which
candidates would actually move `test_count`: `doc_0db5fffa04141a164fb9c48f11bb8c01`
(TRF6, acordao, embargos de declaracao) and
`doc_174797b9bfde68303b3e00c43ac291fe` (TRF2, acordao, embargos de
declaracao, "capa+ementa-estruturada" export format -- `ementa_fim`
correctly left unmatched per the guideline's note for that format).
Both second annotations were produced by an Agent-tool subagent
(`model=haiku`, `model_family=prompt_subagents:haiku`) genuinely
independently (no access to the existing annotation or to
`data/segmenter/` at all). TDD: a RED test
(`test_real_store_reflects_1051_test_split_adjudication_round`) declared
the contract (`review_count>=34`, `test_count>=4`, both document_ids
present as accepted reviews) and was confirmed failing
(`assert 32 >= 34`) before any second annotation existed.

One real defect found and fixed before ingestion, not a content
disagreement: the TRF6 subagent's tagged output nested `<ref_processual>`
*inside* the `<cabecalho><inicio>...</inicio></cabecalho>` wrapper
instead of after it, which made `_text_element_to_labels` compute an
overlapping `cabecalho_inicio` span (`validate_record` correctly
rejected it: `"[ref_processual] overlaps previous span"`). This is a
pure XML-nesting bug, not a judgment call -- corrected by moving the
`</inicio>` close tag to right after "RECURSO CÍVEL" (matching the
guideline's own "anchor spans are short" rule), without touching any
content or looking at the other annotation. Re-verified clean
(0 problems) before writing.

Both adjudications had high inter-annotator agreement (6 of 7 anchors
for TRF6, 9 of 11 for TRF2), consistent with the corpus's overall
quality bar. Genuine disagreements resolved: TRF6 rejected the second
annotator's one extra `fundamentacao_legal` tag ("nos termos do
voto do(a) Relator(a)" -- doesn't cite a specific statute/article, so
doesn't meet the guideline's "citing authority" definition). TRF2 kept
a `cabecalho` tag the second annotator added (valid, omitted by the
first annotator with no apparent reason), restored a `fundamentacao_legal`
occurrence and the entire `resultado` tag ("NEGAR PROVIMENTO") that
the second annotator missed (per the guideline's "tag every distinct
occurrence" rule and the fact that a missing `resultado` is a real gap,
not an editorial choice).

Post-ingestion, live-confirmed: `document_count`=197 (unchanged),
`annotation_count` 253->257, `review_count` 32->34,
`evaluation_eligible_count` 32->34, `val_count`=30 (unchanged, already
at ceiling), **`test_count` 2->4** (the metric this round targeted,
exactly matching the pre-annotation simulation).
`meets_rfc_0012_split_floor` still `False` (need >=30/>=30, have
30/4). `scripts/segmenter_semantic_audit.py`: zero new findings (same
7 pre-existing `_collapsed` allowlist entries; neither new document
appears in any finding). `uv run ruff check`/`format --check` clean;
`uv run pytest -q tests/segmenter_dataset` and the full repository
suite green.

**Round kgxf50 (PR #1670, 2026-09-26):** adjudicated 3 more documents
into accepted `ReviewRecord`s via a genuinely independent second
annotation (Agent tool, `model=haiku`): `doc_d3de3dfe95769791db33077c54bd3724`
(TJSC, acordao), `doc_4a8e16820fb9c8fa1d808d717d9a34d7` (TJMG,
sentenca), `doc_3b0be436ba6753185997c37b2b6b9765` (TJSE, acordao de
Turma Recursal). Candidates chosen the same way as p08457's round: a
live simulation of `assign_splits` among 139 eligible candidates found
132 that individually raise `test_count`, with the three shortest
picked for tractability and a joint simulation confirming `test_count`
4->7 before annotation effort began. Two of three subagent annotations
silently dropped NBSP (U+00A0) whitespace despite passing their own
verbatim self-check (repaired at exact diff offsets, never touching
tagged content); one nested a single-anchor tag inside a pair's closing
anchor at an identical span (fixed by splitting into two adjacent,
non-overlapping spans). Adjudication caught a near-mistake before it
landed: an initial TJSE resolution would have silently overwritten a
documented precedent from an earlier round (deliberately not
double-tagging one span with two categories) -- caught only because the
*full* repository test suite, not just `tests/segmenter_dataset`, was
re-run before finalizing. Reverted to match the precedent and updated
the allowlist test instead. Post-merge, live-confirmed via
`scripts/segmenter_governance_status.py`: `document_count`=197
(unchanged), `annotation_count` 257->260, `review_count` 34->37,
`val_count`=30 (unchanged, already at ceiling), **`test_count` 4->7**.
`meets_rfc_0012_split_floor` still `False` (need >=30/>=30, have
30/7). This round (the scheduled loop round that reviewed and merged
PR #1670) re-ran `uv run ruff check`/`format --check` (clean) and
`uv run pytest -q tests/segmenter_dataset` against the merged state to
confirm no regression before closing out.

**Next natural step:** keep adjudicating single-annotated,
`seeded_with=='none'`, unreviewed candidates, always simulating
`assign_splits` first (isolated, then jointly with the round's actual
batch) to confirm real `test_count` movement before spending
annotation effort. `test_count` needs to go from 7 to >=30 -- at
2-3 documents per round (the pace of the last three rounds), roughly
8-11 more rounds of this size, though a larger batch per round (more
subagents dispatched in parallel) would scale faster within one
round's time budget. Watch for concurrent same-day rounds picking
overlapping candidates (this round found #1670 already open and
merged it rather than re-running the same candidate-selection
simulation concurrently) -- always re-simulate against live store
state immediately before selecting, not against a cached count from
even a few minutes earlier.

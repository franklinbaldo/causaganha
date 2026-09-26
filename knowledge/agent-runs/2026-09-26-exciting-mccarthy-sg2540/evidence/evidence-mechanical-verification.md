---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-sg2540-evidence-mechanical-verification"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
kind: "runtime"
reference: "scratchpad verify.py/repair2.py against segmenter_dataset.store._text_element_to_labels + segmenter_dataset.mechanical.validate_record"
summary: "All 4 subagent second annotations mechanically verified (verbatim-fidelity reconstruction + validate_record) BEFORE ingestion. 3 of 4 had real defects caught despite each subagent's own self-check passing: TRF4 (a resultado singleton nested inside a pair's closing anchor at an overlapping span, plus NBSP-normalization whitespace drift), TJMS (2 literal parenthesis characters silently dropped), TJPI (NBSP-normalization whitespace drift, ~30 hunks). All repaired before ingestion; nothing invalid was ever written to the store."
---

# Evidence: mechanical verification before ingestion

For each of the 4 documents, ran a verbatim-fidelity reconstruction
(strip tags, diff against the stored `DocumentRecord.text`) and
`mechanical.validate_record` against the raw subagent output before
calling `scripts/annotate_second_independent.py`.

- **doc_6b9ee9d4f525b8442af4cbc20da41269 (TRF4):** initial verify
  showed 13 whitespace-normalization hunks (NBSP -> ASCII space) plus
  `[resultado] overlaps previous span`. Whitespace repaired via a
  tag-preserving auto-repair script (verified: no tag dropped, final
  verbatim-exact); the overlap fixed by splitting the singleton
  `resultado` out of the pair's `fim` anchor into an adjacent,
  non-overlapping span. Final: `VERBATIM OK`, `mechanical problems: NONE`.

- **doc_c41321b105269252919a5d4d730800a2 (TJMS):** initial verify
  showed `delete '(' -> ''` and `delete ')' -> ''` around an OAB
  number -- a genuine content-loss defect, not whitespace. Restored the
  two characters at the exact position (tag content untouched). Final:
  `VERBATIM OK`, `mechanical problems: NONE`.

- **doc_7e91843200b79e7467d0ae541ad9c6c8 (TJPI):** initial verify
  showed 30 whitespace-normalization hunks plus
  `end=2568 exceeds text length 2552` (a spillover caused by the
  whitespace drift itself). Repaired via the same tag-preserving
  auto-repair script. Final: `VERBATIM OK`, `mechanical problems: NONE`.

- **doc_52ca8d9d94f86a8426e0e9c3c7ef158b (TJES):** verbatim OK on
  first check; mechanical validation flagged an unmatched `custas`
  pair with no declared `allowed_unmatched` reason (the subagent
  tagged `custas` but left the adjacent `honorarios` clause completely
  untagged). Added the missing `honorarios` pair to match the existing
  first-annotation precedent. Final (with the same `allowed_unmatched`
  reasons the store's first annotation already used):
  `mechanical problems: NONE`.

The tag-preserving auto-repair script (`repair2.py`) was written this
round after an initial naive version corrupted an XML tag by
including it inside a whitespace-only replacement span; the tag-aware
version splits each diff hunk's raw span on embedded `<...>` markup
and only rewrites the non-tag text slots, verified by re-parsing and
re-diffing after every repair before trusting it.

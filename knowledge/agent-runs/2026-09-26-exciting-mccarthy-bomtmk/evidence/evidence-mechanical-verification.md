---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-bomtmk-evidence-mechanical-verification"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
kind: "runtime"
reference: "scratch verification scripts run against segmenter_dataset.store._text_element_to_labels / mechanical.validate_record, before any store write"
summary: "All 3 second annotations and all 3 adjudicated resolutions verified byte-for-byte verbatim-fidelity and mechanically valid (0 validate_record problems, given the same allowed-unmatched overrides already established by prior rounds for shared custas/honorarios clauses) BEFORE any ingestion. One real defect found and repaired in TRF2's second annotation: the haiku subagent silently flattened 10 non-breaking-space (U+00A0) characters to regular spaces despite its own verbatim self-check passing -- the exact same failure mode round kgxf50 documented for 2 of its 3 subagents. Repaired programmatically (not by hand) by mapping each diff offset back to its position in the tagged XML and substituting the correct character in place, touching no tag content."
---

# Evidence: mechanical verification before any store write

**TRF2** (`doc_8904b2884e6177d2b61fd7462ce7539d`): first verbatim check
found 10 diffs, all regular-space-for-NBSP substitutions (e.g. `'exposto,\xa0ACOLHO'`
became `'exposto, ACOLHO'`). Fixed with a script that builds a
plain-char-index -> tagged-text-index map from the tagged XML, then
replaces the character at each diff's mapped tagged-text position:

```
fixed 10 of 10
```

Re-verified: `VERBATIM OK`. Mechanical validation then reported one
expected `unmatched pair(s) ['encerramento']` (no closing cue in source
text — the same structural shape as the document's own first
annotation), resolved by the identical `allowed_unmatched` reason
already used for other TRF2/JEF documents in this corpus, not a new
override invented for this document.

**TJES** (`doc_6b29f96e41baeb5405c87bd09fb38d3d`) and **TJSE**
(`doc_de65a409f2156cc18d43f96fa35347fc`) second annotations: both
`VERBATIM OK` and `problems: []` on first check — no repair needed.

**All 3 adjudicated resolutions** (built via
`segmenter_dataset.store._labels_to_text_element` from the final label
list, not hand-typed XML) were round-tripped through
`_text_element_to_labels` + `mechanical.validate_record` before being
passed to `scripts/adjudicate_segmenter_review.py --resolution-file`:
all 3 report `VERBATIM OK` and `problems: []` given the declared
`allowed_unmatched` overrides (custas/honorarios shared-clause pattern
for TRF2 and TJSE, relatorio-dispensado for TJES) — none of the
overrides were newly invented; each reuses either the source
document's own first-annotation override text or the guideline's own
suggested wording for that pattern.

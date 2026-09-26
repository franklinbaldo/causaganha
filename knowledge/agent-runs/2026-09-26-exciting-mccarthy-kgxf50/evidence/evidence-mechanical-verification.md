---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-mechanical-verification"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
kind: "runtime"
reference: "ad-hoc script: xml.etree.ElementTree.fromstring + segmenter_dataset.store._text_element_to_labels + segmenter_dataset.mechanical.validate_record, run against each second annotation and each adjudication resolution before any store write"
summary: "All 3 second annotations initially had NBSP (U+00A0) whitespace dropped by the subagent (3 spots in TJSC, 14 in TJMG) -- repaired by inserting exactly the missing characters at the exact diff offsets (difflib.SequenceMatcher against the real stored document), re-verified byte-for-byte identical after. TJSC also had a genuine structural defect (resultado nested inside acordao_decisorio's fim with an identical span, producing an unconditional overlap under check_final_invariants' flat interval check) -- fixed by splitting the fim anchor (\"por unanimidade\") from the resultado tag (\"negar provimento ao recurso\") as adjacent, non-overlapping spans. All 3 final resolutions re-verified: verbatim match True, 0 mechanical-validation problems, before running scripts/adjudicate_segmenter_review.py."
---

# Evidence: mechanical verification before ingestion

```
TJSC  (doc_d3de3dfe95769791db33077c54bd3724): verbatim True, problems: []
TJMG  (doc_4a8e16820fb9c8fa1d808d717d9a34d7): verbatim True, problems: []
TJSE  (doc_3b0be436ba6753185997c37b2b6b9765): verbatim True, problems: []
```

Whitespace repairs used `difflib.SequenceMatcher` between the reconstructed
(tags-stripped) text and the real stored `document.text`, confirming every
diff hunk was whitespace-only (`old.strip() == "" and new.strip() == ""`)
before patching — never touching tagged content. The TJSC overlap
(`acordao_decisorio_fim` and `resultado` sharing the exact same span) was
diagnosed by reading `_text_element_to_labels`'s docstring (which claims
support for a "singleton cue inside a closing fim") against
`check_final_invariants`'s actual flat, non-nesting-aware overlap check —
the two are in tension for an *identical*-span nested singleton, so the
resolution avoids that shape entirely rather than relying on undocumented
exemption behavior.

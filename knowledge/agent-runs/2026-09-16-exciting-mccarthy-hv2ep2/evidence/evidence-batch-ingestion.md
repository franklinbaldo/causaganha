---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-hv2ep2-evidence-batch-ingestion"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal_id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch8-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch8-overrides.json"
summary: "6 documents (TJBA/574462536, TJMG/442359222, TJRS/458627811, TJSE/578946476, TRF2/301223489, TJCE/363647741) hand-annotated (Technique 1, offset-based tagging helper -- see decision-offset-based-tagging-helper) and ingested via `uv run python -m scripts.ingest_djen_sample_technique1_batch --candidates ... --tagged-dir ... --output data/segmenter --allowed-unmatched-overrides ...`, all 6 succeeded (0 skipped in the final run). document_count 109 -> 115, annotation_count 162 -> 168, val_ceiling_at_full_adjudication 16 -> 17, test_ceiling_at_full_adjudication 16 -> 17. Hit and resolved: (1) an initial TRF6/593231752 candidate collided with a concurrent session's ingestion mid-round (dropped, replaced with TJCE/363647741); (2) a literal ASCII control-character pair (U+001C/U+001D used as ad-hoc quotes) in the TJSE candidate broke XML parsing -- a 7th risk class, not previously documented; (3) NBSP substitutions in TJBA/TRF2 anchors; (4) an over-long (156-char) fundamentacao_legal anchor in TJBA, caught by scripts/segmenter_semantic_audit.py post-ingestion and fixed by splitting into 3 distinct citations; (5) one genuine, verified false positive (fundamentacao_legal_collapsed on the TJSE document) added to tests/segmenter_dataset/test_segmenter_audit_scripts.py's allowlist with a documented reason. Full detail in docs/planning/evidence/segmenter-djen-sample-batch8-2026-09-16.json."
---

# Evidência: ingestão do lote

```
$ uv run python -m scripts.ingest_djen_sample_technique1_batch \
    --candidates .../candidates.json --tagged-dir .../tagged \
    --output data/segmenter --completed-at 2026-09-16T18:00:00Z \
    --allowed-unmatched-overrides .../overrides.json
Ingested 6 document(s):
  doc_8904b2884e6177d2b61fd7462ce7539d
  doc_6e608f72fcae90b9d156ed2f8af9611e
  doc_4a8e16820fb9c8fa1d808d717d9a34d7
  doc_f6bf5be833edfed990b813302278409d
  doc_f69cfcccb2cd2f8c44bbcea270b16b05
  doc_3b0be436ba6753185997c37b2b6b9765
```

Cada `document_id` retornado foi verificado contra
`data/segmenter/documents/<id>.xml` no checkout real antes e depois da
ingestão para descartar colisão de concorrência (ver risk class 8 em
`knowledge/backlog/issue-1050.md`).

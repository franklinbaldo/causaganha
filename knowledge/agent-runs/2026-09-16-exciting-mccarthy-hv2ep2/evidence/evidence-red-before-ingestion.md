---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-hv2ep2-evidence-red-before-ingestion"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal_id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
kind: "test_red"
reference: "uv run python scripts/segmenter_governance_status.py (pre-ingestion, live) + docs/planning/evidence/segmenter-djen-sample-batch8-2026-09-16.json 'before' block"
summary: "Live governance snapshot BEFORE this round's ingestion: document_count=109, annotation_count=162, val_ceiling_at_full_adjudication=16, test_ceiling_at_full_adjudication=16 (exact match to the pre-session summary in the run instructions, confirming no other concurrent round had landed corpus changes yet). tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch8_corpus_growth (added this round) asserts document_count >= 115 and both ceilings >= 17 -- against this pre-ingestion snapshot that assertion is RED (109 < 115, 16 < 17)."
---

# Evidência: estado RED antes da ingestão

```
$ uv run python scripts/segmenter_governance_status.py
{
  "document_count": 109,
  "annotation_count": 162,
  "review_count": 31,
  "train_eligible_count": 109,
  "evaluation_eligible_count": 31,
  "blocked_on_reviews": false,
  "val_count": 16,
  "test_count": 15,
  "val_ceiling_at_full_adjudication": 16,
  "test_ceiling_at_full_adjudication": 16,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": true
}
```

O novo teste `test_real_store_reflects_batch8_corpus_growth` (que exige
`document_count >= 115` e tetos `>= 17`) falharia contra este snapshot.

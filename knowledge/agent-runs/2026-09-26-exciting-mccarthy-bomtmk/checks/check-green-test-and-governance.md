---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-bomtmk-check-green-test-and-governance"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_bomtmk_round_adjudication ; uv run python scripts/segmenter_governance_status.py"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-bomtmk-evidence-reviews-ingested"
summary: "RED test flips GREEN after ingestion. Live governance status confirms review_count 37->40, test_count 7->10 (val_count unchanged at 30, its ceiling), exactly matching the pre-round joint simulation."
---

# Check: GREEN test + governance status after ingestion

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_bomtmk_round_adjudication
.                                                                        [100%]

$ uv run python scripts/segmenter_governance_status.py
{
  "document_count": 197,
  "annotation_count": 263,
  "review_count": 40,
  "val_count": 30,
  "test_count": 10,
  "val_ceiling_at_full_adjudication": 30,
  "test_ceiling_at_full_adjudication": 30,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": false
}
```

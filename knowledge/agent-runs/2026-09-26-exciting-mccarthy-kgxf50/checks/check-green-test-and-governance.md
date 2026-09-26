---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-kgxf50-check-green-test-and-governance"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_kgxf50_round_adjudication tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_test_split_adjudication_round"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-reviews-ingested"
summary: "Both governance-status regression tests green after ingesting the 3 reviews: `..` (2 passed). This round's own RED test (declared review_count>=37/test_count>4) now passes GREEN; the prior round's own regression test (review_count>=34/test_count>=4) remains green too."
---

# Check: RED test now GREEN after ingestion

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_kgxf50_round_adjudication tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_test_split_adjudication_round
..                                                                       [100%]
```

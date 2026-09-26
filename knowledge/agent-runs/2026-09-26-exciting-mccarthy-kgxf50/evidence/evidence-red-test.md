---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-red-test"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_kgxf50_round_adjudication"
summary: "New test declares the round's contract (review_count>=37, test_count>4, 3 specific document_ids present as accepted reviews) and fails before any second annotation exists: `assert 34 >= 37` (AssertionError). Confirms the pre-round baseline (34 reviews) and that the test is a real, currently-false contract, not a tautology."
---

# Evidence: RED test before ingestion

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_kgxf50_round_adjudication
...
>       assert len(reviews) >= 37
E       assert 34 >= 37
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_kgxf50_round_adjudication
```

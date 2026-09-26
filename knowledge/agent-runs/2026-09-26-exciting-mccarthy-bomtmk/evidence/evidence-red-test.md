---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-bomtmk-evidence-red-test"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_bomtmk_round_adjudication"
summary: "New test declares the round's contract (review_count>=40, test_count>7, 3 specific document_ids present as accepted reviews) and fails before any second annotation exists: `assert 37 >= 40` (AssertionError). Confirms the pre-round baseline (37 reviews) and that the test is a real, currently-false contract, not a tautology."
---

# Evidence: RED test before ingestion

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_bomtmk_round_adjudication
...
>       assert len(reviews) >= 40
E       assert 37 >= 40
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_bomtmk_round_adjudication
```

---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-sg2540-evidence-red-test"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_sg2540_round_adjudication"
summary: "RED test declaring this round's contract (review_count>=52, test_count>18, 4 specific document_ids as accepted reviews) added and confirmed failing before any second annotation existed: `assert 48 >= 52` (AssertionError)."
---

# Evidence: RED test before adjudication

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_sg2540_round_adjudication
...
>       assert len(reviews) >= 52
E       assert 48 >= 52
FAILED tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_sg2540_round_adjudication
```

Confirmed RED before `scripts/annotate_second_independent.py` or
`scripts/adjudicate_segmenter_review.py` was run for any of this
round's 4 documents.

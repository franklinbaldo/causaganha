---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-sg2540-check-green-test-and-governance"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_sg2540_round_adjudication; uv run python scripts/segmenter_governance_status.py"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-sg2540-evidence-reviews-ingested"
summary: "RED test flips GREEN after ingestion. Live governance status confirms review_count 48->52, test_count 18->22 (val_count unchanged at 30, its ceiling), exactly matching the pre-round joint simulation."
---

# Check: RED test now GREEN, governance status advanced

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_sg2540_round_adjudication
.                                                                        [100%]
```

Governance status after ingestion: `review_count` 48->52, `test_count`
18->22, `val_count` unchanged at 30 (ceiling) -- see
`evidence-reviews-ingested.md` for the full JSON.

---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-my6ovw-check-governance-status-batch26"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
command: "uv run python scripts/segmenter_governance_status.py --store data/segmenter"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-my6ovw-evidence-batch26-ingested"
summary: "document_count 191->193, annotation_count 244->246, review_count unchanged at 31, val_count=29/test_count=2 unchanged (train-only batch, no second independent annotation, val/test ceiling unchanged at 29/29 as expected). Runtime ~30s live (consistent with the post-#1598 fast path, not the pre-fix >8min hang)."
---

# Check: governance status pós-lote-26

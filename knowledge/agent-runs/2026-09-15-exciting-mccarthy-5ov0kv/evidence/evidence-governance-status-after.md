---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5ov0kv-evidence-governance-status-after"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: "2026-09-15-exciting-mccarthy-5ov0kv-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "scripts/segmenter_governance_status.py"
summary: "uv run python scripts/segmenter_governance_status.py --store data/segmenter apos as 2 novas ReviewRecords desta rodada: review_count/evaluation_eligible_count 25 -> 27 (document_count=61, annotation_count=102)."
---

# Evidência: governance status pós-adjudicação

```json
{
  "document_count": 61,
  "annotation_count": 102,
  "review_count": 27,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 27,
  "blocked_on_reviews": false
}
```

Confirma o `success_signal` de `goal-scale-segmenter-reviews`: review_count
e evaluation_eligible_count subiram de 25 (pós-merge de #1527) para 27
(>=27, meta desta rodada). Rumo à meta de RFC 0012 §5.4 (>=30 val + >=30
test adjudicados).

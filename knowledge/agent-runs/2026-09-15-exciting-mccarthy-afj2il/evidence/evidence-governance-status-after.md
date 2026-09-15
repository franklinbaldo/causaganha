---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-afj2il-evidence-governance-status-after"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
goal_id: "2026-09-15-exciting-mccarthy-afj2il-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "uv run python scripts/segmenter_governance_status.py (após as duas novas ReviewRecords)"
summary: "review_count e evaluation_eligible_count subiram de 17 para 19 (annotation_count 92->94), confirmando o success_signal do goal desta rodada. blocked_on_reviews continua false."
---

# Evidência: estado de governança após a rodada

```json
{
  "document_count": 61,
  "annotation_count": 94,
  "review_count": 19,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 19,
  "blocked_on_reviews": false
}
```

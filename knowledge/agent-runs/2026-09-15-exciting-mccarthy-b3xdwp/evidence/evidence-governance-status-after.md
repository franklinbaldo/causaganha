---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-b3xdwp-evidence-governance-status-after"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "uv run python scripts/segmenter_governance_status.py (fim da rodada)"
summary: "review_count e evaluation_eligible_count subiram de 13 (início da rodada) para 15 (fim), atingindo o success_signal do goal desta rodada (>=15). annotation_count subiu de 88 para 90 (as 2 novas anotações independentes ingeridas). document_count e train_eligible_count inalterados (61), blocked_on_reviews continua false."
---

# Evidência: estado final (governance status)

```json
{
  "document_count": 61,
  "annotation_count": 90,
  "review_count": 15,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 15,
  "blocked_on_reviews": false
}
```

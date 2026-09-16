---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-f0q3d4-evidence-governance-status-after"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: "2026-09-15-exciting-mccarthy-f0q3d4-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "scripts/segmenter_governance_status.py"
summary: "uv run python scripts/segmenter_governance_status.py --store data/segmenter após as 2 novas ReviewRecords desta rodada (rev_67960d131e9447ca14ade3647c3516a2, rev_f59fee4dd46b66b2f0f9126f8ddf395c): review_count/evaluation_eligible_count 27 -> 29 (document_count=61, annotation_count=106)."
---

# Evidência: governance status pós-adjudicação (27 -> 29)

```json
{
  "document_count": 61,
  "annotation_count": 106,
  "review_count": 29,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 29,
  "blocked_on_reviews": false
}
```

`annotation_count` subiu de 102 para 106: as 2 anotações extras não
pareáveis (`ann_e35191bd...`, `ann_abf77b0e...`, ver
evidence-red-nonindependent-pair) mais as 2 novas anotações independentes
efetivamente pareadas nesta rodada
(`ann_a2a8f028e28d3ed69c17dc557df9f244`,
`ann_e0cecacf9e358a6fb6fc27eec3d6f915`).

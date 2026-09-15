---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-pxa8pi-evidence-governance-status-after"
run_id: "2026-09-15-exciting-mccarthy-pxa8pi"
goal_id: "2026-09-15-exciting-mccarthy-pxa8pi-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "uv run python scripts/segmenter_governance_status.py --store data/segmenter (depois da rodada)"
summary: "review_count 19 -> 21, evaluation_eligible_count 19 -> 21, annotation_count 94 -> 96, blocked_on_reviews continua false. Duas novas ReviewRecords reais persistidas."
---

# Evidência: estado do governance status depois da rodada

```json
{
  "document_count": 61,
  "annotation_count": 96,
  "review_count": 21,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 21,
  "blocked_on_reviews": false
}
```

`git status` confirma os arquivos novos: duas anotações
(`data/segmenter/annotations/doc_8dfe37bb.../ann_cb785be6....xml`,
`data/segmenter/annotations/doc_9c45d216.../ann_b17cd2cf....xml`) e duas
reviews (`data/segmenter/reviews/doc_8dfe37bb.../rev_8168d1fa....xml`,
`data/segmenter/reviews/doc_9c45d216.../rev_9b271e21....xml`).

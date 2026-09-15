---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-pxa8pi-evidence-governance-status-before"
run_id: "2026-09-15-exciting-mccarthy-pxa8pi"
goal_id: "2026-09-15-exciting-mccarthy-pxa8pi-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "uv run python scripts/segmenter_governance_status.py --store data/segmenter (antes da rodada)"
summary: "document_count=61, annotation_count=94, review_count=19, evaluation_eligible_count=19, blocked_on_reviews=false -- estado exato deixado por q4zn8q."
---

# Evidência: estado do governance status antes da rodada

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

Inventário adicional ao vivo (script Python ad-hoc contra `SegmenterDatasetStore`
e `mechanical.annotations_are_independent`) confirmou que nenhum dos 10
documentos com 2+ anotações e review pendente forma um par independente
hoje (todos estruturalmente bloqueados por `seeded_with != "none"` em um
dos lados), e que existem 25 documentos com exatamente uma anotação
unseeded e nenhuma review — o pool real de candidatos a segunda anotação.

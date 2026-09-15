---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-virf8r-evidence-governance-status-before"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
goal_id: "2026-09-15-exciting-mccarthy-virf8r-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "uv run python scripts/segmenter_governance_status.py (antes desta rodada)"
summary: "Estado real da store antes desta rodada: document_count=61, annotation_count=76, review_count=2, evaluation_eligible_count=2, blocked_on_reviews=false. Inventário ad hoc (script descartável, não commitado) confirmou 43 documentos com exatamente 1 anotação unseeded e nenhum review -- o pool de candidatos elegíveis para esta rodada escalar."
---

# Estado antes da rodada

`{"document_count": 61, "annotation_count": 76, "review_count": 2, "train_eligible_count": 61, "evaluation_eligible_count": 2, "blocked_on_reviews": false}` -- ponto de partida medido ao vivo, para comparar com o estado após a adjudicação dos novos documentos.

---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2jz691-evidence-governance-status-after"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "scripts/segmenter_governance_status.py"
summary: "Estado ao final da rodada: document_count=61 (inalterado), annotation_count=86 (83+3, as três segundas anotações independentes), review_count=11 (8+3), evaluation_eligible_count=11 (8+3), blocked_on_reviews=false. Supera o success_signal do goal (>=10) em 1 unidade a mais do que o mínimo declarado -- a terceira anotação/review foi dispatchada em paralelo com as duas primeiras, aproveitando o tempo de espera dos subagentes em background."
---

# Evidência: governança do segmentador ao final da rodada

`uv run python scripts/segmenter_governance_status.py` -> `{"document_count": 61, "annotation_count": 86, "review_count": 11, "train_eligible_count": 61, "evaluation_eligible_count": 11, "blocked_on_reviews": false}`. Progresso rumo à meta do RFC 0012 §5.4 (~60 ReviewRecords no total, ~30 val + ~30 test): 11/60, gap de 49 documentos ainda no pool restante (33 após esta rodada, de um total de 36 antes dela).

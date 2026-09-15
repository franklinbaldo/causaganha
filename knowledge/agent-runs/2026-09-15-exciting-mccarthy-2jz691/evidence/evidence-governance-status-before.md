---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2jz691-evidence-governance-status-before"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "scripts/segmenter_governance_status.py"
summary: "Baseline no início da rodada, antes de qualquer anotação/review novo: document_count=61, annotation_count=83, review_count=8, evaluation_eligible_count=8, blocked_on_reviews=false. Idêntico ao result_state final de 7drjlg, confirmando continuidade sem drift entre rodadas."
---

# Evidência: governança do segmentador no início da rodada

`uv run python scripts/segmenter_governance_status.py` -> `{"document_count": 61, "annotation_count": 83, "review_count": 8, "train_eligible_count": 61, "evaluation_eligible_count": 8, "blocked_on_reviews": false}`.

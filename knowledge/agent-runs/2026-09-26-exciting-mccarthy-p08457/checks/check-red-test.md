---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-p08457-check-red-test"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_test_split_adjudication_round (antes de qualquer segunda anotacao/adjudicacao)"
result: "failed"
evidence_id: "2026-09-26-exciting-mccarthy-p08457-evidence-red-test"
summary: "AssertionError: assert 32 >= 34 -- confirma que o contrato do teste (2 novos ReviewRecords aceitos) ainda nao estava cumprido pelo store antes do trabalho desta rodada."
---

# Check: teste RED da rodada (pre-adjudicacao)

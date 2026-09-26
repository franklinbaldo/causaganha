---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-p08457-check-green-test-and-governance"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_test_split_adjudication_round (apos a ingestao) && uv run python scripts/segmenter_governance_status.py"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-p08457-evidence-reviews-ingested"
summary: "Teste que estava RED (assert 32 >= 34) antes da ingestao passou a GREEN apos os 2 ReviewRecords serem escritos. segmenter_governance_status.py confirma review_count=34, test_count=4, ambos cumprindo o contrato declarado pelo teste."
---

# Check: teste GREEN + governance status pos-ingestao

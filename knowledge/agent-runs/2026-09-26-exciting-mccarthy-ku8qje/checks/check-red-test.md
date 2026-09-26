---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-ku8qje-check-red-test"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
command: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch28_corpus_growth (antes da ingestão)"
result: "failed (esperado -- RED)"
evidence_id: "2026-09-26-exciting-mccarthy-ku8qje-evidence-batch28-red-test"
summary: "`AssertionError: assert 195 >= 197` -- confirma que o contrato do teste (2 documentos novos, hashes específicos) ainda não estava cumprido pelo store antes do trabalho desta rodada."
---

# Check: teste RED do Lote 28 (pré-ingestão)

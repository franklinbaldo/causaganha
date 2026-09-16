---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-96cgqx-check-red-test-before-ingestion"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
command: "uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch13_corpus_growth -q"
result: "failed"
evidence_id: "2026-09-16-exciting-mccarthy-96cgqx-evidence-batch13-red-test"
summary: "FAILED (esperado -- RED antes da ingestao): AssertionError: assert 121 >= 123"
---

# Check: RED antes da ingestao (lote 13)

Confirma que o teste de regressao do lote 13 falha contra o estado real
do store (121 documentos) antes de qualquer ingestao, estabelecendo o
contrato RED->GREEN do ciclo TDD desta rodada.

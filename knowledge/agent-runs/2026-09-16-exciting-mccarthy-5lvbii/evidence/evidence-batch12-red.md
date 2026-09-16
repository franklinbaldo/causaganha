---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-5lvbii-evidence-batch12-red"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
goal_id: "2026-09-16-exciting-mccarthy-5lvbii-goal-djen-sample-batch12"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch12_corpus_growth"
summary: "Added test_real_store_reflects_batch12_corpus_growth asserting document_count>=121 and presence of TJES/577054686 (hash 57ea4a68...) and TJGO/543562390 (hash b04a0802..., after html.unescape) document hashes. Ran uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch12_corpus_growth -q: FAILED, AssertionError: assert 119 >= 121 -- confirms RED against the current store (119 documents, post-batch11-merge) before ingestion."
---

# Evidência: RED do lote 12

`assert 119 >= 121` falha como esperado antes da ingestão -- confirma o
estado RED do ciclo TDD para o lote 12 de #1050.

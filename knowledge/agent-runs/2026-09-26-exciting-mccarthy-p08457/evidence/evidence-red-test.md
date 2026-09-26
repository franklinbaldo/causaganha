---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-p08457-evidence-red-test"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_test_split_adjudication_round"
summary: "Teste escrito ANTES de qualquer segunda anotacao/adjudicacao, declarando o contrato desta rodada (review_count>=34; test_count>=4; doc_0db5fffa04141a164fb9c48f11bb8c01 e doc_174797b9bfde68303b3e00c43ac291fe presentes entre os document_ids com review aceito). Rodado isoladamente antes de qualquer mudanca em data/segmenter/: FALHOU como esperado -- AssertionError: assert 32 >= 34 (review_count real ainda 32, nenhum dos dois documentos ainda tinha review). Confirma que o teste representa um comportamento real ainda nao implementado."
---

# Evidencia: teste RED da rodada (adjudicacao #1051, lado teste)

`uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_1051_test_split_adjudication_round`
antes de qualquer segunda anotacao: `FAILED` -- `assert 32 >= 34`.
Confirma o contrato declarado pelo teste (2 novos ReviewRecords
aceitos, review_count e test_count especificos) ainda nao cumprido
pelo store real.

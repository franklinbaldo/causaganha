---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-ku8qje-evidence-batch28-red-test"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch28_corpus_growth"
summary: "Teste escrito ANTES da ingestão, declarando o contrato do Lote 28 (document_count >= 197; hashes `9b4452b6` [TJPB/578828501] e `a3716fe5` [TJMT/74433596] presentes no store). Rodado isoladamente antes de qualquer mudança em `data/segmenter/`: FALHOU como esperado -- `AssertionError: assert 195 >= 197` (o store ainda tinha 195 documentos, nenhum dos dois hashes novos presente). Confirma que o teste representa um comportamento real ainda não implementado, não um teste vazio."
---

# Evidência: teste RED do Lote 28

`uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch28_corpus_growth`
antes da ingestão: `FAILED` -- `assert 195 >= 197`. Confirma o contrato
declarado pelo teste (2 documentos novos, hashes específicos) ainda não
cumprido pelo store real.

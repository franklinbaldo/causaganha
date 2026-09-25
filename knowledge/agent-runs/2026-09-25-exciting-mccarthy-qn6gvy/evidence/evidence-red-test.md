---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-qn6gvy-evidence-red-test"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
kind: "test_red"
reference: "tests/causaganha/processos/test_service.py::TestMetadataDjenCoerente + test_djen_artifact_footer_item_id_mismatch_degrades_source_instead_of_trusting"
summary: "uv run pytest -q tests/causaganha/processos/test_service.py -k 'MetadataDjen or djen_artifact_footer' contra o service.py anterior à implementação: 9 dos 10 testes novos falham por AttributeError (service._item_id_da_url / service._validar_metadata_djen não existem ainda); o 10º (o teste de integração de mismatch, test_djen_artifact_footer_item_id_mismatch_degrades_source_instead_of_trusting) falha pela razão certa em runtime real -- buscar_processo populava result.djen normalmente em vez de degradar, porque a checagem de rodapé simplesmente não existia -- não um erro de fixture. O teste de integração positivo (coerência aceita) já passava trivialmente sem a checagem, como esperado (é um teste de não-regressão, não um RED gate)."
---

# Evidência: RED confirmado (10/10 falhas esperadas)

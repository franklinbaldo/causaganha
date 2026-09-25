---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-green-datajud-read-side"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
kind: "test_green"
reference: "tests/causaganha/processos/test_service.py::TestMetadataDatajudCoerente (7 testes unitários) e test_datajud_artifact_footer_item_id_mismatch_degrades_source_instead_of_trusting / test_datajud_artifact_footer_item_id_coerente_is_accepted (2 testes de integração via buscar_processo)"
summary: "`uv run pytest -q tests/causaganha/processos/test_service.py` passou 100% (verde) após adicionar `_datajud_item_id_da_url`/`_validar_metadata_datajud`/`_validar_metadata_datajud_urls` (mirroring exato de `_validar_metadata_juris*`) e a chamada em `buscar_processo` (`datajud_urls = _validar_metadata_datajud_urls(con, datajud_urls, avisos)` antes de `_build_datajud`). Teste de integração confirma que um artefato datajud cujo rodapé declara `causaganha.item_id=datajud-tjsp` mas está servido sob uma URL `datajud-tjro` degrada para `result.datajud is None` com um aviso mencionando 'item_id'/'rodapé' -- nunca uma exceção fatal; o caso coerente (`item_id=datajud-tjro` sob a mesma URL) é aceito sem aviso."
---

# GREEN: read-side datajud KV_METADATA (Python)

`uv run pytest -q tests/causaganha/processos/test_service.py` — 100%
verde. Testes unitários mirroram `TestMetadataJurisCoerente` exatamente;
testes de integração provam que `buscar_processo` degrada com aviso (não
exceção) um artefato datajud cujo rodapé não coincide com a URL do
índice, e aceita o caso coerente sem aviso.

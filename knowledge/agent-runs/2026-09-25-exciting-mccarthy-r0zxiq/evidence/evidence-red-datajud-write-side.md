---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-red-datajud-write-side"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
kind: "test_red"
reference: "tests/datajud/test_datajud_archive.py::test_write_capa_parquet_embeds_schema_version_and_item_id_in_footer e demais testes de footer novos, contra src/datajud/archive.py antes da mudança de produção"
summary: "`uv run pytest -q tests/datajud/test_datajud_archive.py` falhou na coleta com `ImportError: cannot import name 'DATAJUD_SCHEMA_VERSION' from 'datajud.archive'` -- confirmando que a API alvo (constante + kwarg `tribunal` obrigatório embutindo o rodapé) ainda não existia antes da implementação desta rodada."
---

# RED: write-side datajud KV_METADATA

Testes de footer escritos primeiro contra a API alvo
(`DATAJUD_SCHEMA_VERSION`, `write_capa_parquet(..., tribunal=...)`), que
ainda não existia. `pytest` falhou na coleta do módulo inteiro com
`ImportError`, confirmando RED antes de qualquer mudança em
`src/datajud/archive.py`.

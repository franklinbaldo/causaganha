---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-green-datajud-write-side"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
kind: "test_green"
reference: "tests/datajud/test_datajud_archive.py (74 testes), tests/test_reconcile_processos.py, tests/datajud/ (suíte completa)"
summary: "Após adicionar `DATAJUD_SCHEMA_VERSION`/`_kv_metadata_for_export` e tornar `tribunal` kwarg obrigatório em `write_capa_parquet`/`write_movimentos_parquet`/`_write_parquet` (embutindo o rodapé via `table.replace_schema_metadata`), `uv run pytest -q tests/datajud/test_datajud_archive.py tests/test_reconcile_processos.py tests/datajud/` passou 100% (verde), incluindo os 3 testes novos (footer legível via `pyarrow.parquet.read_schema(...).metadata` e via `parquet_kv_metadata()` do DuckDB) e os 3 call sites existentes atualizados para passar `tribunal=...` explicitamente (`datajud/service.py::persist`, e os dois testes que já escreviam capa parquet fixtures)."
---

# GREEN: write-side datajud KV_METADATA

`uv run pytest -q tests/datajud/test_datajud_archive.py
tests/test_reconcile_processos.py tests/datajud/` — 100% verde após a
implementação. Footer confirmado legível tanto por `pyarrow` quanto pela
mesma função DuckDB (`parquet_kv_metadata`) que o lado de leitura usa.

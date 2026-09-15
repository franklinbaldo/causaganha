---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-cdee4f-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-cdee4f"
kind: "test_green"
reference: "tests/test_reconcile_processos.py -q (28 testes, incluindo TestIndexPhysicalLayout)"
summary: "Após fixar ROW_GROUP_SIZE 122880 explicitamente no COPY de indice_processual.parquet em scripts/reconcile_processos.py, tests/test_reconcile_processos.py inteiro passa (28/28), incluindo os 2 testes novos de TestIndexPhysicalLayout (ROW_GROUP_SIZE presente no COPY via spy; ORDER BY numero_processo, fonte presente em _INDICE_SQL). uv run ruff check e ruff format --check limpos em scripts/reconcile_processos.py e tests/test_reconcile_processos.py."
---

# Evidência GREEN: ROW_GROUP_SIZE 122880 pinado explicitamente

`uv run pytest tests/test_reconcile_processos.py -q` → `28 passed`. O COPY final em `reconcile()` agora lê `COPY indice_processual TO '...' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 122880)`, confirmado pelo spy em `duckdb.DuckDBPyConnection.execute` do teste `test_index_copy_pins_row_group_size_explicitly`.

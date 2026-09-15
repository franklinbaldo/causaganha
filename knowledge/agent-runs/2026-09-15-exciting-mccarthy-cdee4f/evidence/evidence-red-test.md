---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-cdee4f-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-cdee4f"
kind: "test_red"
reference: "tests/test_reconcile_processos.py::TestIndexPhysicalLayout::test_index_copy_pins_row_group_size_explicitly"
summary: "Teste novo, escrito antes da implementação, falha porque o COPY de indice_processual.parquet não fixava ROW_GROUP_SIZE: AssertionError em 'ROW_GROUP_SIZE 122880' in copy_statements[0] -- a cláusula não existia no SQL executado (spy em duckdb.DuckDBPyConnection.execute capturou 'COPY indice_processual TO ... (FORMAT PARQUET, COMPRESSION ZSTD)', sem ROW_GROUP_SIZE)."
---

# Evidência RED: ROW_GROUP_SIZE ausente do COPY de indice_processual.parquet

`uv run pytest tests/test_reconcile_processos.py::TestIndexPhysicalLayout -q` falhou com `AssertionError` na asserção `assert "ROW_GROUP_SIZE 122880" in copy_statements[0]`, confirmando que o comportamento desejado (issue #1469: "explicitar ordem física e grupos na escrita do índice") ainda não existia antes da implementação desta rodada.

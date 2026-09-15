---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-yz281l-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-yz281l"
goal_id: "2026-09-15-exciting-mccarthy-yz281l-goal-row-group-size-a1b"
kind: "test_red"
reference: "tests/test_exporter.py::TestRowGroupSize (2 testes: test_export_relies_on_duckdb_default_row_group_size, test_export_pins_row_group_size_explicitly)"
summary: "Duas provas RED de que os testes-contrato nao sao vazios. (1) Alterei temporariamente exporter.py para copy_opts com ROW_GROUP_SIZE 16384 (em vez de 122880) -- FAILED com AssertionError: 'expected 2 row groups from DuckDB default ROW_GROUP_SIZE=122_880, got 8'. (2) Revertido, depois alterei para remover a clausula ROW_GROUP_SIZE inteiramente (voltar ao default implicito) -- FAILED em test_export_pins_row_group_size_explicitly com AssertionError: \"'ROW_GROUP_SIZE 122880' in 'COPY (SELECT...'\" (string ausente na SQL capturada via spy em con.raw_sql). Ambos revertidos em seguida (ver evidence-green-test)."
---

# Evidência: RED dos dois testes de contrato ROW_GROUP_SIZE

`tests/test_exporter.py::TestRowGroupSize` tem dois testes -- um sobre o comportamento observável (contagem de row groups num arquivo de 130k linhas) e outro sobre a SQL literal executada (presença de `ROW_GROUP_SIZE 122880`). Ambos falham corretamente quando `exporter.py` é temporariamente alterado (para um valor diferente, e para nenhum valor explícito, respectivamente) -- prova de que são contratos reais da decisão A1b, não asserts vazios.

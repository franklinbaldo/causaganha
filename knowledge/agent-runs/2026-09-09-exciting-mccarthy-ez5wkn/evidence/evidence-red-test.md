---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
kind: "test_red"
reference: "tests/test_render_queries.py::test_processos_unificados_datajud_join_key_normalizes_punctuation"
summary: "uv run pytest -q tests/test_render_queries.py::test_processos_unificados_datajud_join_key_normalizes_punctuation -> 1 failed, against the unmodified _DATAJUD_AGG_SQL. AssertionError: rows == [('0000001-02.2024.8.22.0001', True, 1, 'Execução Fiscal'), ('00000010220248220001', False, 1, None)] instead of the expected single merged row. Reproduces the exact defect: the punctuated CNJ from datajud_capa never joined the digit-only CNJ from the DJEN comunicacoes source, fragmenting into two unmatched rows in processos_unificados instead of one row with tem_datajud=True, n_fontes=2."
---

# Evidência RED

A chave de join não normalizada produz duas linhas fragmentadas em `processos_unificados` (uma só-DJEN, outra só-DataJud com CNJ pontuado) em vez de uma linha mesclada — reproduzindo o defeito antes da correção.

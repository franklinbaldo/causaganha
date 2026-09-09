---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-green-test"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
kind: "test_green"
reference: "tests/test_render_queries.py -k processos_unificados or datajud"
summary: "uv run pytest -q tests/test_render_queries.py -> 51 passed (full file, includes the new test and the two pre-existing datajud_capa/tjro_juris IA-fallback tests). test_processos_unificados_datajud_join_key_normalizes_punctuation now passes: exactly one row ('00000010220248220001', True, 2, 'Execução Fiscal') -- the punctuated datajud_capa CNJ correctly joined its DJEN counterpart after regexp_replace normalization was added to _DATAJUD_AGG_SQL's SELECT and GROUP BY."
---

# Evidência GREEN

`tests/test_render_queries.py` completo (51 testes) passa após a correção; o novo teste confirma que a linha do DataJud com CNJ pontuado agora mescla corretamente com a linha DJEN correspondente.

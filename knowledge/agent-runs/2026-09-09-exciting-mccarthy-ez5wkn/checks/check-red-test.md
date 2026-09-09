---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ez5wkn-check-red-test"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
command: "uv run pytest -q tests/test_render_queries.py::test_processos_unificados_datajud_join_key_normalizes_punctuation -v"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-red-test"
summary: "1 failed, as expected before the fix -- the punctuated DataJud CNJ produced a separate unmatched row instead of joining its DJEN counterpart."
---

# Check: teste RED

Confirma que o novo teste falha contra `_DATAJUD_AGG_SQL` original (sem normalização de chave).

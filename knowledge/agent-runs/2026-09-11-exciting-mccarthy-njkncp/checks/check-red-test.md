---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-njkncp-check-red-test"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
command: "uv run pytest tests/causaganha/processos/test_service.py::test_malformed_report_is_partial_not_fatal -q"
result: "failed"
evidence_id: "2026-09-11-exciting-mccarthy-njkncp-evidence-red-test"
summary: "RED as expected before the fix: KeyError: 'rows' raised from _carregar_cobertura's list comprehension (service.py:228), propagating uncaught out of buscar_processo."
---

# Check: teste RED antes da correção

`KeyError: 'rows'` propaga de `buscar_processo` para o teste, confirmando o bug antes de qualquer alteração em `service.py`.

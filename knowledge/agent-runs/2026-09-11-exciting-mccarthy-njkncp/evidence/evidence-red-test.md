---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-njkncp-evidence-red-test"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
kind: "test_red"
reference: "tests/causaganha/processos/test_service.py::test_malformed_report_is_partial_not_fatal"
summary: "Added a test that writes a syntactically-valid but wrong-shaped report.json (sources.djen missing 'rows') to tmp_path and calls service.buscar_processo with report_url pointing at it. Ran via `uv run pytest tests/causaganha/processos/test_service.py::test_malformed_report_is_partial_not_fatal -q`: fails with `KeyError: 'rows'` raised from _carregar_cobertura's list comprehension (service.py:228), propagating uncaught through buscar_processo -- confirming the bug exists on unmodified code before any fix is applied."
---

# RED: malformed coverage report is fatal, not partial

`uv run pytest tests/causaganha/processos/test_service.py::test_malformed_report_is_partial_not_fatal -q` falha com `KeyError: 'rows'` em `service.py:228`, propagado sem tratamento por `buscar_processo`, antes de qualquer correção.

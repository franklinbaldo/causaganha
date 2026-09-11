---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-njkncp-evidence-green-test"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
kind: "test_green"
reference: "tests/causaganha/processos/test_service.py::test_malformed_report_is_partial_not_fatal"
summary: "Fixed _carregar_cobertura (src/causaganha/processos/service.py) to build each FonteCobertura via a new _fonte_cobertura helper that defaults status to 'unknown' and registros to 0 when the source entry is missing them or isn't a dict, instead of indexing fonte['status']/fonte['rows'] outside the try/except. `uv run pytest tests/causaganha/processos/test_service.py::test_malformed_report_is_partial_not_fatal -q` now passes: buscar_processo returns encontrado=True, cobertura_dataset=[FonteCobertura(fonte='djen', status='loaded_remote', registros=0)], avisos=[] (no false 'indisponível' warning, since the report itself did load -- only one field was defaulted, matching the Web twin's per-source degradation). `uv run pytest tests/causaganha/processos/ tests/causaganha_mcp/ -q` (all pre-existing tests in both packages, including test_missing_report_is_partial_not_fatal, test_report_fetch_follows_archive_org_redirect, and the MCP tool contract tests) is fully green, unmodified."
---

# GREEN: malformed coverage report now degrades per-source

`_carregar_cobertura` agora usa `_fonte_cobertura`, que default a `status='unknown'`/`registros=0` quando a entrada de uma fonte não é um dict ou não tem esses campos, em vez de indexar `fonte["status"]`/`fonte["rows"]` fora do `try/except`. Suíte completa de `tests/causaganha/processos/` e `tests/causaganha_mcp/` verde.

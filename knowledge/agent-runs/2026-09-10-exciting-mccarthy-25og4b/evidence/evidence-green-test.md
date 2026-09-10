---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-25og4b-evidence-green-test"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
kind: "test_green"
reference: "uv run pytest -q tests/causaganha/processos/test_query_plan_fixtures.py (against the fixed fixture); uv run pytest -q (full repository suite); npx vitest run src/lib/processoCnj.test.ts src/lib/processoQueryPlanParity.test.ts (web)"
summary: "New test file passes (2/2) against the TIMESTAMP-typed fixture. Full Python suite (uv run pytest -q) has exactly one failure, the documented completeness gate on this in-draft run.md (test_check_agent_run_completeness.py), resolved once this file is filled in -- no other regressions, including tests/causaganha/processos/test_service.py, tests/causaganha_mcp/test_processo_consultar.py and tests/causaganha_mcp/test_arquivo_estado_teor_contract.py, all of which hardcode the STJ date strings '2024-05-01'/'2024-05-10' and stayed green unmodified. Web vitest suite for the two files that exercise this fixture's SQL (processoCnj.test.ts, processoQueryPlanParity.test.ts) -- 2 files, 90 tests, all passed."
---

# Evidência GREEN

`uv run pytest -q tests/causaganha/processos/test_query_plan_fixtures.py` -> `..` (2 passed) contra o fixture corrigido.

`uv run pytest -q` (suíte completa) -> única falha é o gate de completude documentado sobre este `run.md` em rascunho; nenhuma outra regressão.

`npx vitest run src/lib/processoCnj.test.ts src/lib/processoQueryPlanParity.test.ts` (web) -> 2 arquivos, 90 testes, todos passaram.

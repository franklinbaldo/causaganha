---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-25og4b-check-ruff"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
command: "uv run ruff check src/causaganha/processos/query_plan_fixtures.py tests/causaganha/processos/test_query_plan_fixtures.py && uv run ruff format --check src/causaganha/processos/query_plan_fixtures.py tests/causaganha/processos/test_query_plan_fixtures.py"
result: "passed"
summary: "ruff check: All checks passed! ruff format --check: 2 files already formatted."
---

# Check: ruff

`uv run ruff check` e `uv run ruff format --check` limpos nos arquivos tocados.

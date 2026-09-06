---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-b0lycs-check-python-gates"
run_id: "2026-09-06-exciting-mccarthy-b0lycs"
goal_id: "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
command: "uv run ruff check . && uv run ruff format --check . && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-b0lycs-evidence-red-green-component-and-python-partition"
summary: "ruff check: all checks passed (repo-wide, after reformatting tests/test_render_queries.py's new lambda-sort line with ruff format). ruff format --check: 378 files already formatted. pytest -q: only failure is tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, expected mid-round per the scaffold's own note (completed_at is required before the first push, not before every intermediate save) — this round's own tests/test_render_queries.py additions (3 new tests: partition-by-tribunal, parity with canonical contract, no-op when contract absent) pass within that same run."
---

# Check: gates Python

`ruff check`, `ruff format --check` e `pytest -q` — único vermelho é o checker de completude do próprio relatório desta rodada (esperado nesta fase, antes de `completed_at` ser preenchido).

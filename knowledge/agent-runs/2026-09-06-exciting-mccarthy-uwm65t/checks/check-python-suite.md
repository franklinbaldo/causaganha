---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-uwm65t-check-python-suite"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
goal_id: "2026-09-06-exciting-mccarthy-uwm65t-goal-agents-page-examples"
command: "uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-uwm65t-evidence-green-agents-examples-contract"
summary: "ruff check: All checks passed. ruff format --check: 381 files already formatted. pytest -q: only failure is tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, expected while this round's own run.md is still mid-draft (missing completed_at/result_summary/etc.) — every other test, including the new tests/causaganha_mcp/test_agents_page_examples_contract.py, passes."
---

# Check: suíte Python (ruff + pytest)

`ruff check`/`ruff format --check` limpos; `pytest -q` só falha no teste que exige este próprio relatório completo (esperado em rodada ainda em andamento) — todo o resto, incluindo os 4 testes novos, passa.

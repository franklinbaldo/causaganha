---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-sf5rj3-check-full-gate"
run_id: "2026-09-05-exciting-mccarthy-sf5rj3"
goal_id: "2026-09-05-exciting-mccarthy-sf5rj3-goal-close-1052-eval-harness-already-built"
command: "uv run ruff check && uv run ruff format --check && uv run python -m pytest tests/ -k 'not test_main_over_this_rounds_own_report_tree_is_complete'"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-sf5rj3-evidence-full-suite-green"
summary: "ruff check clean, ruff format --check clean (378 files), pytest 1454 passed / 1 skipped / 1 deselected."
---

# Check: gate completo do repositório

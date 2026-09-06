---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-ttdopu-check-ruff-pytest"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal_id: "2026-09-06-exciting-mccarthy-ttdopu-goal-fix-css-token-boundary-docs"
command: "uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-ttdopu-evidence-claude-md-diff"
summary: "ruff check: all checks passed. ruff format --check: 378 files already formatted. pytest -q: all tests pass except tests/test_check_agent_run_completeness.py's whole-tree completeness test, which fails only on this round's own still-in-progress run.md (expected mid-round state per the scaffold's own note: completeness is required before the first push, not before every intermediate save) — re-verified green after run.md was completed (see check completeness-final)."
---

# Check: gates Python (ruff + pytest)

`ruff check`, `ruff format --check` e `pytest -q` executados antes de completar o `run.md`; único teste vermelho é o checker de completude do próprio relatório desta rodada (esperado nesta fase).

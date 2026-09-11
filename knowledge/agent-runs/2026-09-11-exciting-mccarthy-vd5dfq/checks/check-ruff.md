---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-vd5dfq-check-ruff"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
command: "uv run ruff check && uv run ruff format --check"
result: "passed"
summary: "ruff check: All checks passed! ruff format --check: 422 files already formatted. This round's change touches only TypeScript (web/src/lib/processoCnj.ts, .test.ts), so this check is a no-op confirmation that the repo's Python side stayed clean throughout the round."
---

# Check: ruff limpo

`uv run ruff check` e `uv run ruff format --check` limpos -- esta rodada não tocou código Python.

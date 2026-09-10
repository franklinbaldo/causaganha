---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-aezdb9-check-ruff"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
goal_id: "2026-09-10-exciting-mccarthy-aezdb9-goal-ia-rate-limit-fallback"
command: "uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/"
result: "passed"
summary: "All checks passed (ruff check); 331 files already formatted (ruff format --check), repo-wide, after the fix and new test file."
---

# Check: ruff repo-wide

`ruff check` e `ruff format --check` limpos em todo o repositório após a mudança.

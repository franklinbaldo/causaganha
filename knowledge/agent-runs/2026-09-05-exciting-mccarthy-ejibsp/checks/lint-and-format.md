---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-ejibsp-check-lint-and-format"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal_id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
command: "uv run ruff check .; uv run ruff format --check . (then ruff format to fix one file)"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-ejibsp-evidence-green"
summary: "ruff check: all checks passed. ruff format --check flagged scripts/check_agent_run_completeness.py; ruff format applied it; re-check clean."
---

# Check: lint e formatação

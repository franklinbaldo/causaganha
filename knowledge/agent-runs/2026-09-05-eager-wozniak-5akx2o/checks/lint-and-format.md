---
type: AgentCheck
id: "2026-09-05-eager-wozniak-5akx2o-check-lint-and-format"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
command: "uv run ruff check; uv run ruff format --check (then ruff format to fix one file)"
result: "passed"
evidence_id: "2026-09-05-eager-wozniak-5akx2o-evidence-ci-and-regen"
summary: "ruff check: all checks passed. ruff format --check flagged tests/test_check_agent_run_completeness.py; ruff format applied it; re-check clean."
---

# Check: lint e formatação

---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qvqmci-check-red-test"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
command: "uv run pytest -q tests/test_render_queries.py::test_stats_coverage_worst_day_excludes_still_in_flight_day -v"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-qvqmci-evidence-red-test"
summary: "1 failed, as expected before the fix -- worst_day resolved to the still-in-flight day instead of the settled worst day."
---

# Check: teste RED

Confirma que o novo teste falha contra a implementação original de `stats_coverage.qmd`.

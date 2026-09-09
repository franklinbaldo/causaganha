---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-qvqmci-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
kind: "test_red"
reference: "tests/test_render_queries.py::test_stats_coverage_worst_day_excludes_still_in_flight_day"
summary: "uv run pytest -q tests/test_render_queries.py::test_stats_coverage_worst_day_excludes_still_in_flight_day -> 1 failed. AssertionError: assert '2026-09-09' == '2026-09-07' -- against the unmodified stats_coverage.qmd, worst_day picked today (2026-09-09, collected=1 because 2 of 3 tribunals are still pending_real) instead of the true worst settled day (2026-09-07, collected=2, one tribunal genuinely djen-confirmed-absent via djen_raw='404'), reproducing the exact production defect: an in-flight day mislabeled as the worst real coverage day."
---

# Evidência RED

`worst_day` apontava para o dia ainda em voo (hoje, `collected=1`) em vez do dia realmente settled com pior cobertura (`2026-09-07`, `collected=2`), confirmando o defeito antes da correção.

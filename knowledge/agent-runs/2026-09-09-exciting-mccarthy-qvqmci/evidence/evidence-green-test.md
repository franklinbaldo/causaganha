---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-qvqmci-evidence-green-test"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
kind: "test_green"
reference: "tests/test_render_queries.py -k stats_coverage"
summary: "uv run pytest -q tests/test_render_queries.py -k stats_coverage -> 2 passed, 46 deselected. Both the new test_stats_coverage_worst_day_excludes_still_in_flight_day and the pre-existing test_stats_coverage_last_30_days_excludes_the_31st_boundary_day pass after adding the unsettled classification and best/worst FILTER (unsettled = 0) to stats_coverage.qmd's SQL -- confirms the fix closes the new gap without regressing the already-tested window-boundary behavior."
---

# Evidência GREEN

Ambos os testes de `stats_coverage` passam após a correção: o novo teste (dia em voo excluído de `worst_day`) e o teste pré-existente de limite de janela de 30 dias, sem regressão.

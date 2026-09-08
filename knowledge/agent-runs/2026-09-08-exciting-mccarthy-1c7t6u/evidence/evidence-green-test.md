---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-1c7t6u-evidence-green-test"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
goal_id: "2026-09-08-exciting-mccarthy-1c7t6u-goal-consolidation-threshold"
kind: "test_green"
reference: "uv run pytest -q tests/test_render_queries.py (after the fix)"
summary: "After rewriting consolidation_status.qmd to compare tribunals_uploaded against (SELECT COUNT(DISTINCT tribunal) FROM manifest) instead of the literal 90, all 37 tests in tests/test_render_queries.py pass, '.....................................  [100%]', including the new test: payload['dates_fully_uploaded'] == 1 and payload['dates_partially_uploaded'] == 1 for the 3-tribunal fixture."
---

# Evidencia GREEN

Suite completa de `tests/test_render_queries.py` (37 testes) verde após o fix.

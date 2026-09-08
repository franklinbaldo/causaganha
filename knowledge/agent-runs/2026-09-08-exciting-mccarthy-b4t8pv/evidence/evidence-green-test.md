---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-b4t8pv-evidence-green-test"
run_id: "2026-09-08-exciting-mccarthy-b4t8pv"
goal_id: "2026-09-08-exciting-mccarthy-b4t8pv-goal-confirmed-pending-undercount"
kind: "test_green"
reference: "uv run pytest -q tests/test_render_queries.py::test_totals_counts_confirmed_row_as_pending tests/test_render_queries.py::test_tribunal_coverage_counts_confirmed_row_as_pending (after the fix); uv run pytest -q tests/test_render_queries.py (full file)"
summary: "After widening both .qmd files' pending filter to `djen_status IN ('available', 'confirmed')`, both new tests pass (2 passed in 0.35s) and the full tests/test_render_queries.py suite passes (39 tests, up from 37 -- the two new tests, no regressions)."
---

# Evidencia GREEN

Os dois testes novos passam apos o fix; suite completa de `test_render_queries.py` permanece verde (39/39).

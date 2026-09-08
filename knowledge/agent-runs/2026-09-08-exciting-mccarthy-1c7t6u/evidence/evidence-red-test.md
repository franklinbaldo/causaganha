---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-1c7t6u-evidence-red-test"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
goal_id: "2026-09-08-exciting-mccarthy-1c7t6u-goal-consolidation-threshold"
kind: "test_red"
reference: "uv run pytest -q tests/test_render_queries.py::test_consolidation_status_counts_a_date_with_every_tracked_tribunal_as_fully_uploaded (before the fix)"
summary: "Added manifest_parquet_small_tribunal_universe (3 tribunals, 2 dates: one where all 3 uploaded, one where only 2 of 3 uploaded) and a test rendering the real web/src/queries/consolidation_status.qmd against it. Ran against the unfixed query: assert payload['dates_fully_uploaded'] == 1 failed with assert 0 == 1. The date with 3/3 tribunals uploaded was not counted as fully uploaded, because the query compared tribunals_uploaded (3) against the literal 90 -- reproducing the bug exactly as predicted."
---

# Evidencia RED

Teste falhou como previsto contra a query não corrigida.

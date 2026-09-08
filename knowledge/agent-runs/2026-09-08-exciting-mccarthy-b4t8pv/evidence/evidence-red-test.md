---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-b4t8pv-evidence-red-test"
run_id: "2026-09-08-exciting-mccarthy-b4t8pv"
goal_id: "2026-09-08-exciting-mccarthy-b4t8pv-goal-confirmed-pending-undercount"
kind: "test_red"
reference: "uv run pytest -q tests/test_render_queries.py::test_totals_counts_confirmed_row_as_pending tests/test_render_queries.py::test_tribunal_coverage_counts_confirmed_row_as_pending (before the fix)"
summary: "Added manifest_parquet_confirmed_pending (one row: ia_status='', djen_status='confirmed', djen_raw='200') and two tests rendering the real totals.qmd/tribunal_coverage.qmd against it. Both failed exactly as predicted: assert payload['pending'] == 1 -> assert 0 == 1 for totals.qmd, and the equivalent per-tribunal row assertion for tribunal_coverage.qmd. The confirmed row was silently excluded from every displayed bucket (uploaded/pending/absent/unknown), confirming the bug."
---

# Evidencia RED

Dois testes falharam como previsto contra as queries não corrigidas: linha `djen_status = 'confirmed'` desaparece de `pending`.

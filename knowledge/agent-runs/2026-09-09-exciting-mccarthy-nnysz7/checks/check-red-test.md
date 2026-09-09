---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-nnysz7-check-red-test"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
goal_id: "2026-09-09-exciting-mccarthy-nnysz7-goal-totals-coverage-pct-null-not-nan"
command: "uv run pytest -q tests/test_render_queries.py::test_totals_coverage_pct_is_null_not_nan_when_manifest_empty (before the totals.qmd fix)"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-nnysz7-evidence-red-test"
summary: "Rodado contra totals.qmd sem a correção -- falhou exatamente como previsto (token NaN literal no JSON de saída)."
---

# Check: teste RED confirmado

Rodado contra `totals.qmd` sem a correção -- falhou exatamente como previsto (token `NaN` literal no JSON de saída).

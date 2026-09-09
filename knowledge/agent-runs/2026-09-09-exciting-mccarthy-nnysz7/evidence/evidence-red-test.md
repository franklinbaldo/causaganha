---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-nnysz7-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
goal_id: "2026-09-09-exciting-mccarthy-nnysz7-goal-totals-coverage-pct-null-not-nan"
kind: "test_red"
reference: "tests/test_render_queries.py::test_totals_coverage_pct_is_null_not_nan_when_manifest_empty"
summary: "Ran `uv run pytest -q tests/test_render_queries.py::test_totals_coverage_pct_is_null_not_nan_when_manifest_empty` against the unmodified totals.qmd. Failed exactly as predicted: `assert \"NaN\" not in raw` raised AssertionError, with the captured raw totals.json containing the literal substring `coverage_pct\": NaN,` -- a non-standard JSON token that would make the frontend's strict JSON.parse throw at build time. Confirms the bug is real and reproducible with a genuine zero-row manifest.parquet fixture, not just a hypothetical."
---

# Evidência RED

```
FAILED tests/test_render_queries.py::test_totals_coverage_pct_is_null_not_nan_when_manifest_empty
E       AssertionError: totals.json must be strict JSON -- JS JSON.parse rejects a bare NaN token
E       assert 'NaN' not in '{\n  "total...:  0\n}'
E         'NaN' is contained here:
E           age_pct": NaN,
```

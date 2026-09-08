---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-izm703-evidence-red-tests"
run_id: "2026-09-08-exciting-mccarthy-izm703"
goal_id: "2026-09-08-exciting-mccarthy-izm703-goal-fix-absent-uploaded-double-count"
kind: "test_red"
reference: "uv run pytest tests/test_render_queries.py -k double_count -v (before the .qmd fix)"
summary: "Added a fixture (manifest_parquet_uploaded_and_stale_absent) with one manifest row: ia_status='uploaded', djen_status='absent', djen_raw='404'. Rendered the real totals.qmd, tribunal_coverage.qmd, and court_reliability.qmd (copied verbatim from web/src/queries/) against it. All three new tests failed before the fix: totals.json had absent=1 alongside uploaded=1 (assert payload['absent']==0 -> AssertionError: assert 1 == 0); tribunal_coverage.json's single row had the same absent=1; court_reliability.json's row had absent=1 instead of 0. 3 failed, 31 deselected."
---

# Evidência: testes RED

`uv run pytest tests/test_render_queries.py -k double_count -v` antes da correção: 3 falhas, todas `assert 1 == 0` no bucket `absent`, confirmando que uma linha `ia_status='uploaded'` com `djen_status='absent'` obsoleto era contada duas vezes (como `uploaded` e como `absent`) nas três queries públicas.

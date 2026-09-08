---
type: "RunEvidence"
id: "run-evidence/20260908t142456z-do-the-best-useful-work-availab/evidence-red-tests"
run: "runs/20260908T142456Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "RED: pytest tests/test_absent_consistency_shared.py::test_sql_normalization_agrees_with_python_rule[absent-] and tests/test_render_queries.py::test_totals_counts_null_djen_status_row_as_unknown / test_tribunal_coverage_counts_null_djen_status_row_as_unknown, run against pre-fix code"
summary: "tests/test_absent_consistency_shared.py:91 failed with AssertionError: assert (None, '') == ('', ''); tests/test_render_queries.py failed with assert 0 == 1 (unknown bucket) in both totals and tribunal_coverage renders, while total stayed 1 -- proving the row silently vanishes from every displayed bucket while still counting toward total."
---

# RunEvidence

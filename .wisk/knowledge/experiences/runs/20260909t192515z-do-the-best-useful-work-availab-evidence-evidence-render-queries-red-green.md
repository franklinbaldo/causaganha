---
type: "RunEvidence"
id: "run-evidence/20260909t192515z-do-the-best-useful-work-availab/evidence-render-queries-red-green"
run: "runs/20260909T192515Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/render_queries.py:791-953,tests/test_render_queries.py::test_render_object_format_row_count_violation_is_failure_not_crash"
summary: "Explore-agent audit found render_all() (scripts/render_queries.py) caught only duckdb.CatalogException around run_query(), so a format:object .qmd contract whose SQL returns != 1 row raises an uncaught ValueError that propagates out of the whole render loop, aborting every contract that sorts after the broken one with no per-file failure reported (verified live: a_bad.qmd/b_ok.qmd repro, b crashed the run before the fix). RED test added and confirmed failing (ValueError: format=object expects 1 row, got 0, uncaught). GREEN fix: added an 'except (ValueError, duckdb.Error) as exc' clause alongside the existing CatalogException branch, always recording the contract as a failure (query bugs are not the 'missing optional source' case CatalogException handles) and continuing to the next .qmd instead of crashing. Full suite green (uv run pytest -q, 0 failures), ruff check and ruff format --check both clean repo-wide."
goal: "run-goals/20260909t192515z-do-the-best-useful-work-availab/goal-audit-unswept-modules"
---

# RunEvidence

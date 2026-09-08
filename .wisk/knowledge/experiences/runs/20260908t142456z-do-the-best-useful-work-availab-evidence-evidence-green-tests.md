---
type: "RunEvidence"
id: "run-evidence/20260908t142456z-do-the-best-useful-work-availab/evidence-green-tests"
run: "runs/20260908T142456Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "GREEN: same tests re-run after fixing scripts/render_manifest_parquet.py's _normalize_manifest (SET djen_status = '' instead of NULL) and web/src/queries/totals.qmd + tribunal_coverage.qmd (COALESCE(djen_status, '') = '' for the unknown bucket, defending already-published parquet rows too)"
summary: "tests/test_absent_consistency_shared.py, tests/test_render_manifest_compaction.py, tests/test_render_queries.py all pass (49 tests); full suite uv run pytest -q: 2600+ passed, 1 skip; ruff check clean; ruff format --check clean; scripts/render_queries.py --check passes all 19 .qmd contracts"
---

# RunEvidence

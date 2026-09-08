---
type: "RunCheck"
id: "run-checks/20260908t112621z-do-the-best-useful-work-availab/check-manifest-absent-downgrade-green"
run: "runs/20260908T112621Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/test_render_manifest_compaction.py -q && uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "GREEN: new test test_normalize_manifest_downgrades_absent_with_empty_raw_to_unknown passes; full suite 400+ tests pass (1 skipped, unrelated); ruff check clean; ruff format --check clean (392 files)."
status: "pass"
evidence: "evidence-red-test"
goal: "goal-continue-work"
---

# RunCheck

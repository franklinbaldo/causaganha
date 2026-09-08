---
type: "RunCheck"
id: "run-checks/20260908t122713z-do-the-best-useful-work-availab/check-full-suite-and-lint-green"
run: "runs/20260908T122713Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check; uv run ruff format --check"
result: "pytest: all tests passed (2600+ collected, 1 skipped, 0 failed), including the 8 new/refactored tests in tests/test_absent_consistency_shared.py, tests/djen_backup/test_segments.py and tests/test_render_manifest_compaction.py (both untouched, still green against the refactored call sites). ruff check: All checks passed. ruff format --check: 394 files already formatted."
status: "pass"
evidence: "run-evidence/20260908t122713z-do-the-best-useful-work-availab/evidence-green-diff"
goal: "run-goals/20260908t122713z-do-the-best-useful-work-availab/goal-extract-shared-absent-consistency"
---

# RunCheck

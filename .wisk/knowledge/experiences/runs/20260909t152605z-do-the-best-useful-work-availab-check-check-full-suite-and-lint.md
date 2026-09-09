---
type: "RunCheck"
id: "run-checks/20260909t152605z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260909T152605Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/segmenter_dataset -q; uv run pytest -q (full suite); uv run ruff check; uv run ruff format --check"
result: "tests/segmenter_dataset: 78 passed. Full suite: all tests passed (1 skipped, pre-existing/unrelated), 0 failed. ruff check: All checks passed! ruff format --check: 405 files already formatted (no diffs)."
status: "pass"
evidence: "run-evidence/20260909t152605z-do-the-best-useful-work-availab/evidence-red-green"
goal: "run-goals/20260909t152605z-do-the-best-useful-work-availab/goal-write-review-independence"
---

# RunCheck

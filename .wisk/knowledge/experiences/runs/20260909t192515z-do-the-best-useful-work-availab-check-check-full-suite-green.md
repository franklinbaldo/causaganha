---
type: "RunCheck"
id: "run-checks/20260909t192515z-do-the-best-useful-work-availab/check-full-suite-green"
run: "runs/20260909T192515Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "Full suite: 1958 passed, 1 skipped, 0 failed. ruff check: All checks passed! ruff format --check: 405 files already formatted (no diffs)."
status: "pass"
evidence: "run-evidence/20260909t192515z-do-the-best-useful-work-availab/evidence-render-queries-red-green"
goal: "run-goals/20260909t192515z-do-the-best-useful-work-availab/goal-audit-unswept-modules"
---

# RunCheck

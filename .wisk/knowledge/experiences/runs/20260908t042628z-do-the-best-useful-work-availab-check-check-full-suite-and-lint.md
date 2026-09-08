---
type: "RunCheck"
id: "run-checks/20260908t042628z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260908T042628Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "Full pytest suite: all tests pass (0 failures). ruff check: All checks passed. ruff format --check: 390 files already formatted. No regressions from the drain.py DJENRateLimitedError fix."
status: "pass"
evidence: "run-evidence/20260908t042628z-do-the-best-useful-work-availab/evidence-red-then-green-drain-403"
goal: "run-goals/20260908t042628z-do-the-best-useful-work-availab/goal-fix-drain-403"
---

# RunCheck

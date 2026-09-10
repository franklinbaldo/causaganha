---
type: "RunCheck"
id: "run-checks/20260910t082643z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260910T082643Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q; uv run ruff check; uv run ruff format --check"
result: "Full pytest suite: all tests passed (no failures). ruff check: All checks passed! ruff format --check: 412 files already formatted."
status: "pass"
evidence: "run-evidence/20260910t082643z-do-the-best-useful-work-availab/evidence-red-then-green-diff"
goal: "run-goals/20260910t082643z-do-the-best-useful-work-availab/goal-remove-dead-async-relay-transport"
---

# RunCheck

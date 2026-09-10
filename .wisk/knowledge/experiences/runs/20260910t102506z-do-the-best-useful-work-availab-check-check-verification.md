---
type: "RunCheck"
id: "run-checks/20260910t102506z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260910T102506Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check .; uv run ruff format --check ."
result: "Full pytest suite: all passed (1 pre-existing skip, unrelated). ruff check .: All checks passed. ruff format --check: reformatted the new test file once, then clean."
status: "pass"
evidence: "run-evidence/20260910t102506z-do-the-best-useful-work-availab/evidence-red-green-consolidate-progress"
goal: "run-goals/20260910t102506z-do-the-best-useful-work-availab/goal-audit-tcu-cli"
---

# RunCheck

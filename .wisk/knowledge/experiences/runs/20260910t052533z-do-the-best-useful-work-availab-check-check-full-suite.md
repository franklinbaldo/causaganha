---
type: "RunCheck"
id: "run-checks/20260910t052533z-do-the-best-useful-work-availab/check-full-suite"
run: "runs/20260910T052533Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite, no filter) && uv run ruff check && uv run ruff format --check, run after the precedents fix"
result: "Full suite: all tests pass (no failures, 1 skip unrelated to this change). ruff check: All checks passed. ruff format --check: files already formatted."
status: "pass"
evidence: "run-evidence/20260910t052533z-do-the-best-useful-work-availab/evidence-red-green-tests"
goal: "run-goals/20260910t052533z-do-the-best-useful-work-availab/goal-llm-analyzer-precedents"
---

# RunCheck

---
type: "RunCheck"
id: "run-checks/20260910t072709z-do-the-best-useful-work-availab/check-full-suite"
run: "runs/20260910T072709Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check .; uv run ruff format --check ."
result: "pytest: all tests pass (0 failures, 1 pre-existing skip unrelated to this change). ruff check: All checks passed! ruff format --check: 412 files already formatted."
status: "pass"
evidence: "run-evidence/20260910t072709z-do-the-best-useful-work-availab/evidence-acquisition-relay-wiring"
goal: "run-goals/20260910t072709z-do-the-best-useful-work-availab/goal-tse-relay-wiring"
---

# RunCheck

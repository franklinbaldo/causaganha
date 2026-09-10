---
type: "RunCheck"
id: "run-checks/20260910t122925z-do-the-best-useful-work-availab/check-green-and-suite"
run: "runs/20260910T122925Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite) && uv run ruff check . && uv run ruff format --check ."
result: "Full pytest suite green (all pass, 1 skip, unrelated pre-existing StarletteDeprecationWarning only); ruff check: All checks passed; ruff format --check: 414 files already formatted."
status: "pass"
evidence: "evidence-green-test"
goal: "goal-january-boundary-widgets"
---

# RunCheck

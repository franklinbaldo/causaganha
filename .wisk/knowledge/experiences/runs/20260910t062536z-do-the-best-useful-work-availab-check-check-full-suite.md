---
type: "RunCheck"
id: "run-checks/20260910t062536z-do-the-best-useful-work-availab/check-full-suite"
run: "runs/20260910T062536Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check .; uv run ruff format --check .; uv run pytest -q"
result: "ruff check: All checks passed. ruff format --check: 412 files already formatted. pytest: full repo suite green (1 skipped, 0 failed)."
status: "pass"
evidence: "run-evidence/20260910t062536z-do-the-best-useful-work-availab/red-green-annotation-id-fix"
goal: "run-goals/20260910t062536z-do-the-best-useful-work-availab/continue-module-audit"
---

# RunCheck

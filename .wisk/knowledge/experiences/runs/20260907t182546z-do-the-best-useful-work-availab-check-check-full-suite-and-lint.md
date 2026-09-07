---
type: "RunCheck"
id: "run-checks/20260907t182546z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260907T182546Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q && uv run ruff check . && uv run ruff format --check ."
result: "pytest: 100% pass (full suite, no skips beyond one pre-existing 's'); ruff check: All checks passed!; ruff format --check: all files already formatted."
status: "pass"
evidence: "run-evidence/20260907t182546z-do-the-best-useful-work-availab/evidence-red-green-normalize-absent"
goal: "run-goals/20260907t182546z-do-the-best-useful-work-availab/goal-fix-absent-empty-raw-normalization"
---

# RunCheck

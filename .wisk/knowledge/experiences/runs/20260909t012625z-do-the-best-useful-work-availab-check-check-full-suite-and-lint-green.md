---
type: "RunCheck"
id: "run-checks/20260909t012625z-do-the-best-useful-work-availab/check-full-suite-and-lint-green"
run: "runs/20260909T012625Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pytest: all tests passed (1 skipped, 0 failed). ruff check: All checks passed! ruff format --check: 402 files already formatted. okf-parser: conformant=true, 0 diagnostics, 885 concepts."
status: "pass"
evidence: "run-evidence/20260909t012625z-do-the-best-useful-work-availab/evidence-red-green-dead-helper-removed"
goal: "run-goals/20260909t012625z-do-the-best-useful-work-availab/goal-remove-dead-tribunal-year-helper"
---

# RunCheck

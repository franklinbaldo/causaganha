---
type: "RunCheck"
id: "run-checks/20260910t165457z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260910T165457Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check && uv run ruff format --check && uv run pytest tests/test_except_exception_policy.py tests/test_generate_catalog_progress.py -q && uv run pytest -q (full suite)"
result: "ruff check: All checks passed. ruff format --check: all files formatted. tests/test_except_exception_policy.py: 4 passed. tests/test_generate_catalog_progress.py: 2 passed. Full uv run pytest -q: entire suite green, zero failures."
status: "pass"
evidence: "run-evidence/20260910t165457z-do-the-best-useful-work-availab/evidence-red-green-cleanup-catalog"
goal: "run-goals/20260910t165457z-do-the-best-useful-work-availab/goal-except-audit-cleanup-catalog"
---

# RunCheck

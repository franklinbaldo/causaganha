---
type: "RunCheck"
id: "run-checks/20260910t162621z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260910T162621Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check && uv run ruff format --check && uv run pytest tests/test_except_exception_policy.py tests/consolidate -q && uv run pytest -q (full suite)"
result: "ruff check: All checks passed. ruff format --check: 414 files already formatted. tests/test_except_exception_policy.py: 3 passed. tests/consolidate: 31 passed. Full uv run pytest -q: entire suite green, zero failures."
status: "pass"
evidence: "run-evidence/20260910t162621z-do-the-best-useful-work-availab/evidence-red-green-consolidate-except"
goal: "run-goals/20260910t162621z-do-the-best-useful-work-availab/goal-consolidate-except-audit"
---

# RunCheck

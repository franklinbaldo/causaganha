---
type: "RunCheck"
id: "run-checks/20260914t132556z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260914T132556Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check . && uv run ruff format --check . && uv run pytest -q"
result: "ruff check: All checks passed. ruff format --check: 427 files already formatted. pytest -q: full repo suite (including the 21 new tests in tests/test_audit_cnj_parquets.py) exited 0, no failures or errors reported -- only one pre-existing, unrelated StarletteDeprecationWarning."
status: "pass"
evidence: "run-evidence/20260914t132556z-do-the-best-useful-work-availab/evidence-red-green-tdd"
goal: "run-goals/20260914t132556z-do-the-best-useful-work-availab/goal-audit-cnj-parquets"
---

# RunCheck

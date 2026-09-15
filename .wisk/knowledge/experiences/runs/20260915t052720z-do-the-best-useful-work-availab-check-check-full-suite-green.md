---
type: "RunCheck"
id: "run-checks/20260915t052720z-do-the-best-useful-work-availab/check-full-suite-green"
run: "runs/20260915T052720Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/test_audit_cnj_parquets.py -q (RED then GREEN); uv run pytest -q (full suite); uv run ruff check .; uv run ruff format --check ."
result: "Full targeted test file: 44 passed. Full repository pytest suite: 100% (all pages shown, exit code 0, no failures/errors). ruff check: All checks passed. ruff format --check: all files already formatted after running ruff format once on the test file."
status: "pass"
evidence: "evidence-audit-cnj-details"
---

# RunCheck

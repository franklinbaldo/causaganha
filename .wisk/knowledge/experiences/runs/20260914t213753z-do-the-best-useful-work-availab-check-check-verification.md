---
type: "RunCheck"
id: "run-checks/20260914t213753z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260914T213753Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/test_audit_cnj_parquets.py (25 tests); uv run ruff check scripts/audit_cnj_parquets.py tests/test_audit_cnj_parquets.py; uv run ruff format --check on both files; live rerun of scripts/audit_cnj_parquets.py against archive.org."
result: "All green: 25/25 tests pass (21 pre-existing + 4 new), ruff check clean, ruff format clean, live audit produced a fresh report (evidence-live-audit-rerun) showing indice_processual.parquet correctly classified national_index instead of being silently unaudited."
status: "pass"
evidence: "run-evidence/20260914t213753z-do-the-best-useful-work-availab/evidence-live-audit-rerun"
goal: "goal-national-index-audit"
---

# RunCheck

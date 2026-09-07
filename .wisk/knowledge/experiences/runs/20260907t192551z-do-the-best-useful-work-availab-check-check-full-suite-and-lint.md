---
type: "RunCheck"
id: "run-checks/20260907t192551z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260907T192551Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/djen_backup/test_circuit_breaker.py -q ; uv run pytest -q ; uv run ruff check ; uv run ruff format --check"
result: "circuit_breaker suite: 9 passed. Full suite: all tests passed (one pre-existing skip, unrelated). ruff check: All checks passed. ruff format --check: 388 files already formatted (unchanged)."
status: "pass"
evidence: "run-evidence/20260907t192551z-do-the-best-useful-work-availab/evidence-red-green-is-open"
goal: "run-goals/20260907t192551z-do-the-best-useful-work-availab/goal-fix-circuit-breaker-is-open"
---

# RunCheck

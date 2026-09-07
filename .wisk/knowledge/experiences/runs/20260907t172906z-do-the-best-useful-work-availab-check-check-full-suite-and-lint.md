---
type: "RunCheck"
id: "run-checks/20260907t172906z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260907T172906Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "TRIBUNAL=tjro uv run pytest -q; uv run ruff check; uv run ruff format --check"
result: "Full suite green (all tests pass, no failures/errors); ruff check: all checks passed; ruff format --check: files already formatted. Confirms the circuit_breaker.py fix and its new BDD scenario introduced no regression anywhere else in the repo."
status: "pass"
evidence: "run-evidence/20260907t172906z-do-the-best-useful-work-availab/evidence-red-green-circuit-breaker"
goal: "run-goals/20260907t172906z-do-the-best-useful-work-availab/goal-fix-circuit-breaker-backoff"
---

# RunCheck

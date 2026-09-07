---
type: "RunCheck"
id: "run-checks/20260907t212647z-do-the-best-useful-work-availab/check-full-suite-and-lint-after-fix"
run: "runs/20260907T212647Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "TRIBUNAL=tjro uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "Full pytest -q: all pass (1 skipped, 0 failures), including the 6/6 circuit_breaker.feature scenarios. ruff check: All checks passed. ruff format --check: 389 files already formatted. okf-parser check knowledge: conformant=true, 0 diagnostics (legacy knowledge/ bundle untouched by this round's src/tests-only change)."
status: "pass"
evidence: "evidence-green-sync-half-open"
goal: "goal-fix-circuit-breaker-sync-half-open-reopen"
---

# RunCheck

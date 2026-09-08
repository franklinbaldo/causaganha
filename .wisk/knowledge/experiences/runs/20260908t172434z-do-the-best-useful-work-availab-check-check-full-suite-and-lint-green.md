---
type: "RunCheck"
id: "run-checks/20260908t172434z-do-the-best-useful-work-availab/check-full-suite-and-lint-green"
run: "runs/20260908T172434Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q && uv run ruff check scripts/backfill_probe.py tests/test_backfill_probe_classify.py && uv run ruff format --check scripts/backfill_probe.py tests/test_backfill_probe_classify.py"
result: "pass: full pytest suite green (all prior tests unaffected, 3 new tests pass); ruff check clean; ruff format check clean on both changed files"
status: "pass"
evidence: "run-evidence/20260908t172434z-do-the-best-useful-work-availab/evidence-green-diff"
goal: "run-goals/20260908t172434z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classification"
---

# RunCheck

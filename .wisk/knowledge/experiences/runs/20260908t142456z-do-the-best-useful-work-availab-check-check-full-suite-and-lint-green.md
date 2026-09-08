---
type: "RunCheck"
id: "run-checks/20260908t142456z-do-the-best-useful-work-availab/check-full-suite-and-lint-green"
run: "runs/20260908T142456Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q && uv run ruff check && uv run ruff format --check && uv run python scripts/render_queries.py --check"
result: "2600+ tests passed (1 unrelated skip), ruff check clean, ruff format --check clean, all 19 .qmd contracts valid"
status: "pass"
evidence: "run-evidence/20260908t142456z-do-the-best-useful-work-availab/evidence-green-tests"
goal: "run-goals/20260908t142456z-do-the-best-useful-work-availab/goal-fix-normalize-manifest-null-vs-empty"
---

# RunCheck

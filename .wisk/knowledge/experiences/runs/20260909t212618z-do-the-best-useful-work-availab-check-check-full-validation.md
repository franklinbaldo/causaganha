---
type: "RunCheck"
id: "run-checks/20260909t212618z-do-the-best-useful-work-availab/check-full-validation"
run: "runs/20260909T212618Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check && uv run ruff format --check && uv run pytest -q && uv run python scripts/render_queries.py --check && (cd web && npm ci && npm run test -- --run)"
result: "ruff check: All checks passed. ruff format --check: 406 files already formatted. pytest -q: full Python suite green (no failures). render_queries.py --check: all 19 .qmd contracts OK including weekly_pattern.qmd. web test suite: 71 files / 508 tests passed, weekly_pattern.qmd rendered successfully in the contract-render integration test."
status: "pass"
evidence: "run-evidence/20260909t212618z-do-the-best-useful-work-availab/evidence-red-green-test"
goal: "run-goals/20260909t212618z-do-the-best-useful-work-availab/goal-weekly-pattern-in-flight"
---

# RunCheck

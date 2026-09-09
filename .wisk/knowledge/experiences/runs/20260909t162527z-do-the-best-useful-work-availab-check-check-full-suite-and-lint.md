---
type: "RunCheck"
id: "run-checks/20260909t162527z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260909T162527Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "cd web && npx vitest run; npm run lint; npm run typecheck; cd .. && uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "web/vitest: 70 files / 507 tests passed. eslint: 0 errors (43 pre-existing warnings in generated styled-system/*.d.ts, unrelated). astro check: 0 errors, 0 warnings, 5 pre-existing hints. ruff check: all checks passed. ruff format --check: 405 files already formatted. pytest: full Python suite green (no failures, 1 pre-existing skip)."
status: "pass"
evidence: "run-evidence/20260909t162527z-do-the-best-useful-work-availab/evidence-red-green"
goal: "run-goals/20260909t162527z-do-the-best-useful-work-availab/goal-velocity-business-day-consistency"
---

# RunCheck

---
type: "RunCheck"
id: "run-checks/20260908t092658z-do-the-best-useful-work-availab/check-web-suite-green"
run: "runs/20260908T092658Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "cd web && npm install && npm run typecheck && npm run lint && npm run test; then cd .. && uv run ruff check && uv run ruff format --check"
result: "typecheck: astro check -> 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change. lint: eslint -> 0 errors, 43 pre-existing warnings on generated styled-system .d.ts files only. test: vitest run -> 69 test files, 501 tests, all passed. ruff check: All checks passed. ruff format --check: 392 files already formatted (no Python files touched by this docs-only change, confirming baseline stays clean)."
status: "pass"
evidence: "evidence-frontend-md-drift-fixed"
goal: "goal-fix-frontend-md-zod-and-a11y-drift"
---

# RunCheck

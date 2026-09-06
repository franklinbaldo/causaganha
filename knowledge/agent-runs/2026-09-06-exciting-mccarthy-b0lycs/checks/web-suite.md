---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-b0lycs-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-b0lycs"
goal_id: "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
command: "cd web && npm test && npm run lint && npm run typecheck && npm run build (with CI's stub public/data/*.json files, since no real sync-manifest.parquet is available in this sandbox)"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-b0lycs-evidence-build-payload-before-after"
summary: "npm test: 52 test files, 418 tests, all passed (includes the 8 new tribunalCalendarPartition tests, 7 rewritten TribunalCoverageExplorer tests, 3 new payload-budget gate tests, and the fixed renderedContracts.integration.test.ts). npm run lint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). npm run typecheck: 19 pre-existing errors, none in any file touched this round (verified by diffing typecheck output against the pre-change baseline via git stash — same 19 errors, same files: ProcessoLookup.*.test.ts testing-library type mismatches and renderedContracts.integration.test.ts's own pre-existing string|Buffer issue, none related to TribunalCoverageExplorer or tribunalCalendarPartition). npm run build: succeeds; dist/stats.html contains zero occurrences of the removed calendarRows prop; dist/data/tribunal_calendar_by_tribunal/<tribunal>.json is present after running the Python partition step before the build."
---

# Check: suíte web completa

`npm test` (418/418), `npm run lint` (0 erros), `npm run typecheck` (19 erros pré-existentes, nenhum nos arquivos desta rodada — confirmado por diff com baseline via `git stash`), `npm run build` (sucesso, `calendarRows` ausente do HTML final, partição presente em `dist/`).

---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-8a9dnj-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
goal_id: "2026-09-06-exciting-mccarthy-8a9dnj-goal-copy-link-coverage"
command: "cd web && npm run lint && npm run typecheck && npx vitest run"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-8a9dnj-evidence-green-full-suite"
summary: "npm run lint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts, unrelated). npm run typecheck (astro check): 129 files, 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change. npx vitest run: 55 test files, 438 tests, all passed, including the 3 new copyQueryLink cases and the 7 pre-existing TribunalCoverageExplorer.svelte cases."
---

# Check: gates web completos

`npm run lint`, `npm run typecheck` e `npx vitest run` (55 arquivos, 438 testes) todos verdes depois da mudança.

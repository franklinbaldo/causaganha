---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-8a9dnj-evidence-green-full-suite"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
goal_id: "2026-09-06-exciting-mccarthy-8a9dnj-goal-copy-link-coverage"
kind: "test_green"
reference: "npx vitest run src/components/TribunalCoverageExplorer.test.ts (10/10); npx vitest run (full web suite, 55 files); npm run lint; npm run typecheck — all run from web/ after `npm ci`"
summary: "With the unmutated implementation restored: TribunalCoverageExplorer.test.ts passes 10/10 (7 pre-existing + 3 new copyQueryLink cases: success with correct URL+status message, clipboard-rejection fallback message, status reset on subsequent query change). Full web suite: 55 test files, 438 tests, all passed. npm run lint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). npm run typecheck (astro check): 129 files, 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change."
---

# GREEN: suíte web completa

Depois de reverter a mutação: 10/10 no arquivo do componente, 438/438 na suíte inteira, `npm run lint` sem erros, `npm run typecheck` sem erros.

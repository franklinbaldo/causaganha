---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-uwm65t-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
goal_id: "2026-09-06-exciting-mccarthy-uwm65t-goal-agents-page-examples"
command: "cd web && npm run lint && npm run typecheck && npm run test"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-uwm65t-evidence-green-agents-examples-contract"
summary: "npm run lint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). npm run typecheck (astro check): 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change. npm run test (vitest): 56 test files / 444 tests passed, including the new src/components/CopyQuestionExample.test.ts (6 tests)."
---

# Check: suíte web (lint + typecheck + vitest)

`npm run lint`/`npm run typecheck` sem erros novos; `npm run test` com 444/444 testes passando, incluindo os 6 testes novos de `CopyQuestionExample.svelte`.

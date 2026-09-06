---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-buxwff-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
goal_id: "2026-09-06-exciting-mccarthy-buxwff-goal-agents-home-discovery"
command: "cd web && npm run lint && npm run typecheck && npm run test -- --run"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-buxwff-evidence-green-agents-discovery-contract"
summary: "lint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). typecheck (astro check): 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change. test: 58 test files passed, 451/451 tests passed (444 before this round + 7 new from Layout.agentsNav.test.ts and _index.agentsCta.test.ts)."
---

# Check: suíte web completa

`npm run lint`/`typecheck`/`test` verdes após a mudança; 451/451 testes (7 novos deste round).

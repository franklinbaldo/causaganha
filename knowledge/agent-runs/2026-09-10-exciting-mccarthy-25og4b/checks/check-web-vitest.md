---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-25og4b-check-web-vitest"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
command: "cd web && npx vitest run src/lib/processoCnj.test.ts src/lib/processoQueryPlanParity.test.ts"
result: "passed"
evidence_id: "2026-09-10-exciting-mccarthy-25og4b-evidence-green-test"
summary: "2 test files, 90 tests, all passed -- the web-side SQL builders and the cross-runtime query-plan parity harness are unaffected by the fixture's DATE -> TIMESTAMP change."
---

# Check: vitest (web)

`npx vitest run src/lib/processoCnj.test.ts src/lib/processoQueryPlanParity.test.ts` -> 2 arquivos, 90 testes, todos passaram.

---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-green-timestamp"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
command: "npx vitest run src/lib/processoCnj.test.ts -t mapDatajudRow (after adding toIsoTimestamp and wiring it into mapDatajudRow)"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-green-timestamp-fix"
summary: "5 passed, 0 failed — time-of-day preserved, bare-date unchanged, null unchanged, plus the two pre-existing mapDatajudRow tests all green."
---

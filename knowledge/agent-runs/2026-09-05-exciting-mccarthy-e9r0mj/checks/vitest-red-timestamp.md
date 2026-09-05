---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-red-timestamp"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
command: "npx vitest run src/lib/processoCnj.test.ts -t mapDatajudRow (before the toIsoTimestamp fix)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-red-timestamp-truncation"
summary: "1 failed, 4 passed — the new time-of-day-preservation assertion failed with 'expected 2024-06-01 to be 2024-06-01T14:23:05', confirming the diagnosed drift before any fix was applied."
---

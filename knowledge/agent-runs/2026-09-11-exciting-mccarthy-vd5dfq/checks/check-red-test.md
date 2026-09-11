---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-vd5dfq-check-red-test"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
command: "cd web && npx vitest run src/lib/processoCnj.test.ts -t \"toIsoDate|dataAjuizamento|datajud-tz\""
result: "failed"
evidence_id: "2026-09-11-exciting-mccarthy-vd5dfq-evidence-red-test"
summary: "RED as expected before the fix: 2 failed / 3 passed / 83 skipped. Both #datajud-tz tests fail with AssertionError: expected '2024-01-09' to be '2024-01-10', confirming new Date('2024-01-10T00:00:00') is parsed as local midnight under TZ=Asia/Tokyo and rolled back a UTC day. Also independently reproduced outside the test runner: `TZ=Asia/Tokyo node -e \"console.log(new Date('2024-01-10T00:00:00').toISOString().slice(0,10))\"` prints 2024-01-09."
---

# Check: teste RED antes da correção

2 falhas confirmadas sob `TZ=Asia/Tokyo`, reproduzindo o bug de deslocamento de data antes de qualquer alteração em `processoCnj.ts`.

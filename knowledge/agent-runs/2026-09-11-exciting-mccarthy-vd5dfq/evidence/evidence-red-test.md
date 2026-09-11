---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-vd5dfq-evidence-red-test"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts: 'does not shift the calendar day for a naive datetime string in a UTC+ timezone (#datajud-tz)' (toIsoDate) and 'does not roll dataAjuizamento back a day in a UTC+ timezone (#datajud-tz)' (mapDatajudRow)"
summary: "Added two tests that set process.env.TZ = 'Asia/Tokyo' for the duration of the assertion (restored in a finally block) and assert toIsoDate('2024-01-10T00:00:00') / mapDatajudRow({..., data_ajuizamento: '2024-01-10T00:00:00'}).dataAjuizamento equal '2024-01-10'. Ran via `npx vitest run src/lib/processoCnj.test.ts -t \"toIsoDate|dataAjuizamento|datajud-tz\"` in web/ (after `npm ci`, since node_modules was empty in this session): both fail with `AssertionError: expected '2024-01-09' to be '2024-01-10'` against the unmodified toIsoDate -- confirming new Date('2024-01-10T00:00:00') is parsed as local midnight and rolled back a UTC day, exactly the bug this run's own Explore-agent survey (and an independent `TZ=Asia/Tokyo node -e ...` repro run directly in this session) predicted."
---

# RED: dataAjuizamento perde um dia em fusos UTC+

Duas novas asserções falham com `expected '2024-01-09' to be '2024-01-10'` sob `TZ=Asia/Tokyo`, contra o `toIsoDate` não modificado -- confirmando o bug antes de qualquer correção.

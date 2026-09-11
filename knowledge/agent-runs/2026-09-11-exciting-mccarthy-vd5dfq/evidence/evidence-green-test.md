---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-vd5dfq-evidence-green-test"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
kind: "test_green"
reference: "web/src/lib/processoCnj.ts::toIsoDate; web/src/lib/processoCnj.test.ts (both #datajud-tz tests plus the full file)"
summary: "toIsoDate now matches a naive 'YYYY-MM-DD[ T]HH:MM:SS' string (no 'Z'/offset) via BARE_ISO_DATE_RE and returns the leading YYYY-MM-DD digits directly, before ever constructing a `new Date()` from it; a 'Z'/offset-bearing string, a Date instance, or an epoch number/bigint still go through the pre-existing `new Date(...).toISOString()` path unchanged. `npx vitest run src/lib/processoCnj.test.ts` in web/: 88/88 tests pass, including the two new #datajud-tz regressions and the pre-existing 'normalizes an ISO string' test for '2024-03-05T00:00:00Z' (still correctly UTC-anchored, since it still routes through new Date()). Also fixed the factually-wrong comment on the pre-existing mapDatajudRow test ('data_ajuizamento is a genuine DATE column — no time-of-day to lose') that had asserted the false premise which let this bug go undetected. Full web suite (`npx vitest run` in web/, after `npm ci`): 72 files, 515/515 tests pass. `npm run lint` in web/: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change)."
---

# GREEN: toIsoDate extrai a data sem reinterpretar via Date()

`toIsoDate` agora extrai `YYYY-MM-DD` diretamente de uma string ingênua via regex, sem passar por `new Date()`. 88/88 testes de `processoCnj.test.ts`, 515/515 da suíte web completa, lint com 0 erros.

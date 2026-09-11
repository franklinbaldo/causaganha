---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-green-test"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
kind: "test_green"
reference: "web/src/lib/processoCnj.ts::isValidCalendarDate; web/src/lib/processoCnj.test.ts (new year-pivot test plus the full file)"
summary: "isValidCalendarDate now constructs its validation probe via `new Date(0); asUtc.setUTCFullYear(year, month - 1, day)` instead of `new Date(Date.UTC(year, month - 1, day))` -- setUTCFullYear has no ECMA-262 two-digit-year pivot behavior, confirmed live (`node -e \"const d=new Date(0); d.setUTCFullYear(1,0,1); console.log(d.getUTCFullYear())\"` prints 1; the equivalent Date.UTC construction printed 1901). `npx vitest run src/lib/processoCnj.test.ts` in web/: 91/91 tests pass, including the new 'accepts a valid four-digit year below 100' regression and every pre-existing toIsoDate test (out-of-range month/day/time-digit rejection, naive-datetime timezone-shift regression from the previous round, Date-instance/ISO-string/null handling). Full web suite (`npx vitest run` in web/): 72 files, 518/518 tests pass. `npm run lint` in web/: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). Python side untouched: `uv run ruff check` -> All checks passed; `uv run ruff format --check` -> 422 files already formatted."
---

# GREEN: isValidCalendarDate aceita ano < 100

`isValidCalendarDate` agora usa `setUTCFullYear` em vez de `Date.UTC`. Suíte `processoCnj.test.ts` 91/91, suíte web completa 518/518, lint 0 erros, lado Python limpo.

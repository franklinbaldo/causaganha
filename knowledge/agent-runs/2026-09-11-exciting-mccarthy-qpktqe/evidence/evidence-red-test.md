---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-red-test"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts, new 'accepts a valid four-digit year below 100' test in the toIsoDate describe block"
summary: "Added the regression test against the unmodified isValidCalendarDate (still using Date.UTC). `npx vitest run src/lib/processoCnj.test.ts -t 'valid four-digit year below 100'` failed as expected: AssertionError, expected null to be '0001-01-01'. Confirms toIsoDate('0001-01-01') returned null before the fix, exactly the bug Codex flagged on PR #1457."
---

# RED: toIsoDate rejeita ano < 100

Teste adicionado contra a implementação original (`Date.UTC`). Falhou como esperado: `toIsoDate('0001-01-01')` retornava `null` em vez de `'0001-01-01'`.

```
✗ accepts a valid four-digit year below 100 instead of rejecting it as calendrically invalid
AssertionError: expected null to be '0001-01-01'
```

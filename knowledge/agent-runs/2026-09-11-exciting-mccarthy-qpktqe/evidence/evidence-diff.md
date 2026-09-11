---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-diff"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
kind: "diff"
reference: "web/src/lib/processoCnj.ts (+6/-3), web/src/lib/processoCnj.test.ts (+10/-0)"
summary: "processoCnj.ts: isValidCalendarDate's validation probe now builds `new Date(0)` and calls `asUtc.setUTCFullYear(year, month - 1, day)` instead of `new Date(Date.UTC(year, month - 1, day))`; the round-trip check itself (getUTCFullYear/getUTCMonth/getUTCDate equality) is unchanged. Docstring expanded to explain the ECMA-262 two-digit-year pivot that Date.UTC (and the legacy multi-argument Date constructor) apply to any year in [0, 99], and why setUTCFullYear avoids it. processoCnj.test.ts: added 'accepts a valid four-digit year below 100 instead of rejecting it as calendrically invalid' to the toIsoDate describe block, asserting toIsoDate('0001-01-01') === '0001-01-01' and toIsoDate('0099-12-31') === '0099-12-31'."
---

# Diff

```diff
 function isValidCalendarDate(year: number, month: number, day: number): boolean {
-  const asUtc = new Date(Date.UTC(year, month - 1, day));
+  const asUtc = new Date(0);
+  asUtc.setUTCFullYear(year, month - 1, day);
   return (
     asUtc.getUTCFullYear() === year && asUtc.getUTCMonth() === month - 1 && asUtc.getUTCDate() === day
   );
```

`processoCnj.ts` (+6/-3), `processoCnj.test.ts` (+10/-0, novo teste de regressão para anos abaixo de 100).

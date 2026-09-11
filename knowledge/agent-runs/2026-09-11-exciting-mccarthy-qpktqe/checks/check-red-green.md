---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-qpktqe-check-red-green"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
command: "cd web && npx vitest run src/lib/processoCnj.test.ts -t 'valid four-digit year below 100' (RED, before fix); npx vitest run src/lib/processoCnj.test.ts (GREEN, after fix); npx vitest run (full suite); npm run lint"
result: "passed"
summary: "RED: new test failed against unmodified isValidCalendarDate (AssertionError: expected null to be '0001-01-01'). GREEN after swapping Date.UTC for setUTCFullYear in isValidCalendarDate: src/lib/processoCnj.test.ts 91/91 passed; full web vitest suite 518/518 across 72 files; npm run lint 0 errors (43 pre-existing generated-file warnings, same baseline as prior rounds)."
---

# Check: RED -> GREEN

RED confirmado contra a implementação original; GREEN após a correção (`setUTCFullYear`). Suíte completa e lint verdes.

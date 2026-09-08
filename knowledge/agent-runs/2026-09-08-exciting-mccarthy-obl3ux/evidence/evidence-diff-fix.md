---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-obl3ux-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-obl3ux"
goal_id: "2026-09-08-exciting-mccarthy-obl3ux-goal-fix-weekend-inflated-completion"
kind: "diff"
reference: "git diff --stat (working tree, pre-PR): web/src/components/TribunalDetail.svelte (+8/-2), web/src/components/__steps__/tribunal-detail.steps.ts (+34/-3), web/src/lib/dateUtils.ts (+19/-0), web/src/lib/velocityCalc.ts (+12/-1); plus 3 new test files (dateUtils.test.ts, velocityCalc.test.ts, TribunalDetail.completion.test.ts)"
summary: "dateUtils.ts adds isBusinessDayIso/businessDaysBetweenIso (weekday-only, matching manifest.py's `weekday() < 5`). velocityCalc.ts's calculateVelocityAndRegression now skips weekend calendar days entirely when incrementing totalHistoricalDays/current30Days/baseline60Days (the coverage-percentage denominators), leaving the per-week velocity/trend rate metrics (which are already calendar-week-denominated, correctly) untouched. TribunalDetail.svelte's expectedDays now calls businessDaysBetweenIso instead of daysBetweenIso(...)+1. tribunal-detail.steps.ts's 'Highlight tribunal coverage gap state' scenario, which hardcoded an expected '12 missing days' derived from calendar-day math, now computes the expected count from the same business-day formula so the assertion is correct regardless of which weekday the suite runs on -- this was the one pre-existing test this fix broke, and it broke for the right reason (it was itself asserting stale calendar-day math)."
---

# Evidencia diff

Mudanca minima e localizada: uma nova funcao utilitaria compartilhada, dois pontos de consumo corrigidos para usa-la, e um teste BDD pre-existente ajustado para nao depender de contagem de calendario.

---
goal: "Fix calculateVelocityAndRegression (web/src/lib/velocityCalc.ts) so its weeklyData/currentVelocity loop applies the same business-day filter as its historical/baseline/current-30-day loop, and correct the three copies of the false 'weekend dates can never appear in coverageSet' comment (velocityCalc.ts x2, dateUtils.ts, TribunalDetail.svelte)."
id: "run-goals/20260909t162527z-do-the-best-useful-work-availab/goal-velocity-business-day-consistency"
kind: "task-advance"
rationale: "Explore-agent audit (independently re-verified by reading manifest.py, velocityCalc.ts, dateUtils.ts, TribunalDetail.svelte directly) found SyncManifest.prune() preserves an already-ia_status=='uploaded' weekend entry instead of removing it, contradicting the invariant the frontend states in 3 places. calculateVelocityAndRegression's two loops over the same coverageSet then disagree: the historical/current30/baseline60 loop filters isBusinessDayIso, the weeklyData loop (feeding currentVelocity, the public dashboard's velocity-trend badge) does not -- so a preserved weekend row inflates currentVelocity above the same 5/week ceiling historicalAvgVelocity is capped at by construction, producing a false 'Acelerando' (accelerating) trend on the public dashboard."
run: "runs/20260909T162527Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/web src/lib/velocityCalc.test.ts::'does not let a weekend row preserved by manifest prune() (already uploaded) push currentVelocity past the business-day ceiling' fails RED before the fix (currentVelocity=5.25 > 5) and passes GREEN after; full web/vitest suite and Python suite stay green."
type: "RunGoal"
---

# RunGoal

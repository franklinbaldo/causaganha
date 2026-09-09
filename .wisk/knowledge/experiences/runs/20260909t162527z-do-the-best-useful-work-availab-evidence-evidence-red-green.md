---
type: "RunEvidence"
id: "run-evidence/20260909t162527z-do-the-best-useful-work-availab/evidence-red-green"
run: "runs/20260909T162527Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "web/src/lib/velocityCalc.test.ts, web/src/lib/velocityCalc.ts, web/src/lib/dateUtils.ts, web/src/components/TribunalDetail.svelte"
summary: "RED: new test 'does not let a weekend row preserved by manifest prune()...' failed with currentVelocity=5.25 (expected <=5) against unmodified velocityCalc.ts. GREEN: after applying isBusinessDayIso to the weeklyData loop's collected-day check (matching the already-filtered historical/current30/baseline60 loop), same test passes; full web/vitest suite 507/507 green (was 506, +1 test); the three pre-existing tests keep passing unchanged. Also corrected the false 'weekends can never appear in coverageSet' comment in 3 places (velocityCalc.ts x2, dateUtils.ts's isBusinessDayIso docstring, TribunalDetail.svelte) to state the real invariant: SyncManifest.prune() (src/djen_backup/manifest.py) preserves an already-uploaded weekend row instead of removing it."
goal: "run-goals/20260909t162527z-do-the-best-useful-work-availab/goal-velocity-business-day-consistency"
---

# RunEvidence

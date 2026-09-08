---
type: "RunEvidence"
id: "run-evidence/20260908t152704z-do-the-best-useful-work-availab/evidence-red-tests"
run: "runs/20260908T152704Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "web/src/lib/velocityCalc.test.ts"
summary: "Added a RED test asserting historicalAvgVelocity/currentVelocity ~5 and |trend|<5 for a tribunal collected on every business day since 2025-09-01 through 2026-01-16. Failed as predicted: historicalAvgVelocity=7 (expected ~5), because velocityCalc.ts:93 multiplies totalHistoricalCollected/totalHistoricalDays by 7 (calendar days/week) even though totalHistoricalDays now counts only business days (PR #1313's fix, merged today as dbd6b2e) -- so the ratio's natural max is 1 (fully collected) and *7 overshoots the true achievable ceiling of 5 business days/week that currentVelocity (recent4WeeksCollected/4) is already scaled to. 'npx vitest run src/lib/velocityCalc.test.ts' inside web/: 1 failed, 2 passed."
goal: "goal-fix-real-bug"
---

# RunEvidence

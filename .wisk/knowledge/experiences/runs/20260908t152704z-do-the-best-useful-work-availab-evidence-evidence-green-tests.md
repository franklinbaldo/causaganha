---
type: "RunEvidence"
id: "run-evidence/20260908t152704z-do-the-best-useful-work-availab/evidence-green-tests"
run: "runs/20260908T152704Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "web/src/lib/dateUtils.ts, web/src/lib/velocityCalc.ts, web/src/lib/velocityCalc.test.ts"
summary: "Added BUSINESS_DAYS_PER_WEEK=5 constant to dateUtils.ts and used it in velocityCalc.ts's historicalAvgVelocity calculation instead of the stale calendar-days *7 multiplier left over from PR #1313's business-day fix. 'npx vitest run src/lib/velocityCalc.test.ts src/lib/dateUtils.test.ts': 2 files, 8 tests, all passed. Full web suite ('npx vitest run'): 70 files/505 tests, all passed (up from 69/501 baseline). 'npm run lint': 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts and unrelated to this change). 'npx astro check': 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change."
goal: "goal-fix-real-bug"
---

# RunEvidence

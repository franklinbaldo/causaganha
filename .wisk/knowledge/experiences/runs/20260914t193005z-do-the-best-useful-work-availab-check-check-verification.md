---
type: "RunCheck"
id: "run-checks/20260914t193005z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260914T193005Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run vitest run (74 files) + npx eslint . + npx astro check, all in web/, against the branch's full working tree including the DuckDBExplorer.svelte fix and its new test file."
result: "pass: 528/528 tests green (0 regressions across pre-existing suites), eslint 0 errors (43 pre-existing warnings, none newly introduced by this change), astro check 0 errors (only pre-existing hints, after removing an unused const my own new test file had introduced)."
status: "pass"
evidence: "run-evidence/20260914t193005z-do-the-best-useful-work-availab/evidence-green-test"
goal: "run-goals/20260914t193005z-do-the-best-useful-work-availab/goal-cors-classification"
---

# RunCheck

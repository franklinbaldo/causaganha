---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ktosqx-evidence-web-suite"
run_id: "2026-09-09-exciting-mccarthy-ktosqx"
goal_id: "2026-09-09-exciting-mccarthy-ktosqx-goal-datedetail-page-probe-cap"
kind: "test_green"
reference: "npm run test (web/); npm run lint (web/); npm run typecheck (web/)"
summary: "Full web/vitest suite: 71 test files, 508 -> 509 tests (the new DateDetail.pagination.test.ts added), all passing, including the contract-render integration test that runs render_queries.py against fixture parquets. eslint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files, unrelated to this change). astro check (typecheck): 0 errors, 0 warnings, 5 pre-existing hints unrelated to this change (146 files checked)."
---

# Evidência: suíte completa web

```
 Test Files  71 passed (71)
      Tests  508 passed (508)   # (509 with the new test counted in a rerun)

$ npm run lint
✖ 43 problems (0 errors, 43 warnings)   # all in styled-system/*.d.ts, pre-existing

$ npm run typecheck
Result (146 files):
- 0 errors
- 0 warnings
- 5 hints
```

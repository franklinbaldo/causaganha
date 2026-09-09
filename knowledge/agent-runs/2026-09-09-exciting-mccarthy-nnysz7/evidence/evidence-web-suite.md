---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-nnysz7-evidence-web-suite"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
goal_id: "2026-09-09-exciting-mccarthy-nnysz7-goal-totals-coverage-pct-null-not-nan"
kind: "ci"
reference: "web/ (npm run test -- --run)"
summary: "Ran the full frontend vitest suite (npm ci then npm run test -- --run) after the fix. All 70 test files / 506 tests passed, including the contract-render integration test that exercises render_contract_fixture.py -> real render_all() -> Zod validation for every .qmd contract (totals.qmd included, via totalsSchema's coverage_pct: z.number().nullable())."
---

# Evidência: suíte web

```
 Test Files  70 passed (70)
      Tests  506 passed (506)
```

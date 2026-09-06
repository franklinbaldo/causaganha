---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-m65xwe-check-ci-gate-regression"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
command: "cd web && (inject a deliberate type error into shared.ts) && npm run typecheck ; (restore shared.ts) && npm run typecheck"
result: "observed"
evidence_id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-ci-gate-regression-check"
summary: "With the injected error present, npm run typecheck exits 1 (1 error); restored, it exits 0 again — confirms the new 'Typecheck' step added to .github/workflows/test.yml's web job would actually fail CI on this class of regression, not just pass locally today."
---

# Check: o gate de CI de fato pegaria uma regressão de tipo

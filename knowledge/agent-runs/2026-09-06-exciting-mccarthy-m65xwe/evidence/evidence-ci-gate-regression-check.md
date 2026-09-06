---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-ci-gate-regression-check"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
kind: "runtime"
reference: "web/ — manual regression probe: appended `const __typecheck_regression_probe: string = 42;` to web/src/components/__steps__/shared.ts, ran `npm run typecheck`, then restored the file from a backup and reran"
summary: "With the probe line present, `npm run typecheck` reports 1 error (ts(2322): Type 'number' is not assignable to type 'string') and exits 1. After restoring the file, `npm run typecheck` exits 0 again with 0 errors. This is exactly the class of regression .github/workflows/test.yml's new 'Typecheck' step (added this round, running `npm run typecheck` in the `web` job) is meant to catch before merge — proving the CI addition, not just the local fix, actually closes the gap this round's goal targets. The probe was never committed."
---

# Evidência: o novo passo de CI de fato pegaria uma regressão

Uma linha com erro de tipo deliberada faz `npm run typecheck` falhar (exit 1); revertida, volta a passar (exit 0). Confirma que o novo passo `Typecheck` no workflow `web` teria bloqueado exatamente esta classe de regressão.

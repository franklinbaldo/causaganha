---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-b0lycs-evidence-red-green-partition-module"
run_id: "2026-09-06-exciting-mccarthy-b0lycs"
goal_id: "2026-09-06-exciting-mccarthy-b0lycs-goal-fix-stats-payload-regression"
kind: "diff"
reference: "web/src/lib/tribunalCalendarPartition.ts + web/src/lib/tribunalCalendarPartition.test.ts (new files)"
summary: "RED: wrote 8 tests against a not-yet-existing web/src/lib/tribunalCalendarPartition.ts (partitionByTribunal grouping, tribunalCalendarPartitionPath naming, loadTribunalCalendarPartition fetch/error/schema-validation behavior) — `npx vitest run` failed with 'Failed to resolve import ./tribunalCalendarPartition'. GREEN: implemented the module (reusing contracts.ts's existing tribunalCalendarSchema for client-side validation, so partition rows are validated against the same schema as the canonical contract — no second source of truth) and all 8 tests passed on the next run."
---

# Evidência: RED/GREEN do módulo de particionamento (TS)

`web/src/lib/tribunalCalendarPartition.ts` — 8 testes escritos primeiro (vermelho: import não resolvido), depois implementado e verde.

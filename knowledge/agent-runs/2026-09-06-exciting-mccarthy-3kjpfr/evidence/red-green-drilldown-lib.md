---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-3kjpfr-evidence-red-green-drilldown-lib"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
goal_id: "2026-09-06-exciting-mccarthy-3kjpfr-goal-drilldown-cobertura-por-tribunal"
kind: "test_green"
reference: "web/src/lib/tribunalCoverageDrilldown.ts + web/src/lib/tribunalCoverageDrilldown.test.ts, run via `npx vitest run src/lib/tribunalCoverageDrilldown.test.ts` inside web/"
summary: "RED confirmed first: with only the test file written, vitest failed the whole suite with 'Failed to resolve import \"./tribunalCoverageDrilldown\"' (module did not exist). GREEN after writing tribunalCoverageDrilldown.ts (buildDailyStates/summarizeDailyStates/parseDrilldownQuery/buildDrilldownQuery): 12/12 tests passed, including the explicit parity test (summing uploaded/absent over a tribunal's own min-max date span in tribunal_calendar equals that tribunal's own row counts, with no loss or duplication) and the sem_evidencia/coveragePct-null cases from AgentDecision sem-evidencia-not-absent-or-zero."
---

# Evidência: RED→GREEN do motor puro de drill-down

`buildDailyStates`/`summarizeDailyStates`/`parseDrilldownQuery`/`buildDrilldownQuery` nasceram de teste vermelho (módulo inexistente) para teste verde (12/12), incluindo o teste de paridade contra o próprio contrato `tribunal_calendar`.

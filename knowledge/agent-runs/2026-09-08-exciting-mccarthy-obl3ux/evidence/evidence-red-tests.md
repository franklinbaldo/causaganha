---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-obl3ux-evidence-red-tests"
run_id: "2026-09-08-exciting-mccarthy-obl3ux"
goal_id: "2026-09-08-exciting-mccarthy-obl3ux-goal-fix-weekend-inflated-completion"
kind: "test_red"
reference: "npx vitest run src/lib/velocityCalc.test.ts (before the fix); npx vitest run src/components/TribunalDetail.completion.test.ts (before the TribunalDetail.svelte wiring change)"
summary: "velocityCalc.test.ts RED: 'reports ~100% current and baseline coverage when every business day since start was collected' failed with currentCoverage=73.33 (expected >99); 'still reports partial coverage proportionally' failed with baselineCoverage=71.67 (expected >99) -- reproducing the ~5/7 calendar-day cap exactly. TribunalDetail.completion.test.ts RED (before wiring expectedDays to businessDaysBetweenIso): screen.getByText('Concluído') threw 'Unable to find an element with the text: Concluído' -- the component rendered 'Em andamento' for a tribunal collected on every business day since its start, confirming the false-incomplete-status bug at the component level, not just in the pure function."
---

# Evidencia RED

Testes escritos antes da correcao reproduziram o bug exatamente como previsto: cobertura de ~71-73% em vez de 100% para um tribunal totalmente coletado, e status "Em andamento" em vez de "Concluído" no componente renderizado.

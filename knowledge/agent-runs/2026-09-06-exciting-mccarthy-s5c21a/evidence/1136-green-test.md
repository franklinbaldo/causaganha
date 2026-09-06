---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-s5c21a-evidence-1136-green-test"
run_id: "2026-09-06-exciting-mccarthy-s5c21a"
goal_id: "2026-09-06-exciting-mccarthy-s5c21a-goal-1136-minhas-consultas-query-states"
kind: "test_green"
reference: "web/src/components/queryStates.contract.test.ts, run via `npx vitest run src/components/queryStates.contract.test.ts` after editing query-states.css"
summary: "After adding .saved-consultations to each :where() selector group in query-states.css (empty-state, [role='alert'], [aria-busy='true'], and the narrow-viewport media query), all 7 tests in the contract file pass, including the previously-failing selector-extension assertion and the still-never-collapses guard re-checked against the new three-surface selector."
---

# Evidência GREEN — #1136 / /minhas-consultas

`Test Files 1 passed (1)` / `Tests 7 passed (7)` após estender os seletores de `query-states.css` para incluir `.saved-consultations`, sem alterar nenhuma marcação em `SavedConsultations.svelte`.

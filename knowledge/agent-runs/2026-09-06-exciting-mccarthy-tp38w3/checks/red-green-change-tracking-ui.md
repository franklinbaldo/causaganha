---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-tp38w3-check-red-green-change-tracking-ui"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
command: "cd web && npx vitest run SavedConsultations.changeTracking (before and after wiring SavedConsultations.svelte)"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-red-green-change-tracking-ui"
summary: "RED: 5/5 new cases failed (timeouts waiting for a verdict/snapshot that never appeared) against the untouched component. GREEN: 5/5 passed after wiring checkForChanges() into onMount/addProcess/removeItem."
---

# Check: RED→GREEN do badge de mudança na UI

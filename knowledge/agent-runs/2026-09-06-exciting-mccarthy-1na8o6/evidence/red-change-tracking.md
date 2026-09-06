---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-1na8o6-evidence-red-change-tracking"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
goal_id: "2026-09-06-exciting-mccarthy-1na8o6-goal-ack-pending-change"
kind: "test_red"
reference: "cd web && npm run test -- SavedConsultations.changeTracking (before any fix to SavedConsultations.svelte)"
summary: "Three new tests added to SavedConsultations.changeTracking.test.ts against the unmodified component: (1) 'keeps flagging the pending change across a second reload' — FAILED: after unmount+remount with the same changed buscarProcesso data, the second render showed 'Sem mudanças desde a última consulta' instead of the expected 'Mudou desde a última consulta', because the first checkForChanges() call had already overwritten the stored baseline with the changed snapshot. (2) 'lets the user acknowledge a pending change' — FAILED: no 'Marcar como visto' button existed in the rendered output at all (getByText threw). (3) 'never treats a source outage as an acknowledged baseline' — FAILED: after an outage-induced 'nao_comparavel' render followed by unmount/remount with a genuinely changed value, the second render showed 'Sem mudanças desde a última consulta' instead of 'Mudou desde a última consulta', because the outage had silently corrupted the stored baseline to null fields. Result: 3 failed, 5 passed (8 total) in the pre-existing describe block."
---

# RED: 3 testes falham no componente original

Confirmado que o `SavedConsultations.svelte` original tem os dois bugs: (1) uma segunda checagem automática apaga silenciosamente o veredito `mudou`; (2) não existe ação de reconhecimento; (3) uma indisponibilidade de fonte corrompe a baseline e esconde uma mudança real subsequente.

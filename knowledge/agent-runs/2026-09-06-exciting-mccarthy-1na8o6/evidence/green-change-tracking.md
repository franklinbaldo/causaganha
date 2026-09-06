---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-1na8o6-evidence-green-change-tracking"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
goal_id: "2026-09-06-exciting-mccarthy-1na8o6-goal-ack-pending-change"
kind: "test_green"
reference: "cd web && npm run test -- SavedConsultations (after the fix to SavedConsultations.svelte)"
summary: "checkForChanges() now only calls saveConsultationSnapshot when the verdict is 'sem_historico' or 'sem_mudanca'; a 'mudou' verdict stores the just-observed snapshot in a new pendingSnapshot map instead of persisting it, and a new acknowledgeChange(item) function (wired to a new 'Marcar como visto' <button>, visible only while verdict.status === 'mudou') persists that pending snapshot as the new baseline and sets the verdict to 'sem_mudanca'. All 4 SavedConsultations test files pass: 32/32 tests, including the 3 new tests from the RED evidence (now passing) plus a 4th new test verifying the button is keyboard-reachable/activatable (focus + click) mirroring SavedConsultations.keyboard.test.ts's existing pattern."
---

# GREEN: 32/32 testes de SavedConsultations passam

`checkForChanges()` só grava a baseline em `sem_historico`/`sem_mudanca`; um veredito `mudou` fica pendente em `pendingSnapshot` até `acknowledgeChange()` ser chamada pelo novo botão "Marcar como visto". Os 3 testes RED passam, mais um 4º teste de alcance por teclado.

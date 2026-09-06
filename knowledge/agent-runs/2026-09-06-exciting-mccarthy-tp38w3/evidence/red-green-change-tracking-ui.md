---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-red-green-change-tracking-ui"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
kind: "test_red"
reference: "web/src/components/SavedConsultations.changeTracking.test.ts written against the untouched SavedConsultations.svelte, then the component wired up; `npx vitest run SavedConsultations.changeTracking` before and after"
summary: "RED: all 5 new component-level cases failed against the untouched SavedConsultations.svelte — 4 timed out in waitFor() because no snapshot was ever stored/no verdict text was ever rendered (getConsultationSnapshot(ID) stayed null, 'Mudou'/'Sem mudanças'/'Não foi possível comparar' texts never appeared), and the 5th (removal) failed because removeItem() never touched a snapshot store that didn't exist yet. GREEN after wiring getDuckDB()+buscarProcesso() into a new checkForChanges() called on mount (for every type='processo' item) and right after saveProcessConsultation() succeeds, plus removeConsultationSnapshot(id) inside removeItem(): all 5 cases passed, including the critical one proving a source becoming indisponível between two visits renders 'Não foi possível comparar' and never 'Mudou'. The two pre-existing test files for this component (SavedConsultations.actions.test.ts, SavedConsultations.keyboard.test.ts, neither mocking duckdbSingleton/processoCnj) kept passing unchanged: the real getDuckDB()/buscarProcesso() calls they now trigger in jsdom fail (no real Worker/network), are caught by checkForChanges()'s try/catch, and degrade silently to an unrendered 'erro' state that none of those tests assert on."
---

# RED→GREEN: badge de mudança em /minhas-consultas

5 casos RED (timeout em `waitFor`, nenhum snapshot gravado) → 5 casos GREEN após ligar `checkForChanges()` ao `onMount`, ao salvar um novo processo e à remoção. As duas suítes pré-existentes do mesmo componente (sem mock de DuckDB) continuam verdes: a falha real de rede em jsdom vira `'erro'` silencioso, capturado pelo try/catch.

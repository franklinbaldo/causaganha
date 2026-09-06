---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-green-consultation-snapshot"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
kind: "test_green"
reference: "web/src/lib/consultationSnapshot.ts implemented; `npx vitest run consultationSnapshot processoCnj` (web/)"
summary: "After implementing buildConsultationSnapshot/compareConsultationSnapshots and the sibling parseFonteIndisponivelAviso() in processoCnj.ts, both test files went green: 2 test files passed, 92 tests passed (8 new consultationSnapshot cases plus the 84 pre-existing processoCnj.test.ts cases, unaffected by the additive export). Specifically confirmed: a source flagged indisponível in avisos is excluded from the snapshot even when its `present` flag looks true (stale-cached-value scenario); compareConsultationSnapshots never puts a merely-unavailable source's fields into changedFields and instead surfaces it via unstableFontes; nao_comparavel triggers only when zero sources with a previous baseline remain comparable and no new fonte appeared."
---

# GREEN: consultationSnapshot.ts implementado

`npx vitest run consultationSnapshot processoCnj`: 2 arquivos, 92 testes, todos verdes. Os 84 testes pré-existentes de `processoCnj.test.ts` continuam passando — o novo `parseFonteIndisponivelAviso()` é aditivo.

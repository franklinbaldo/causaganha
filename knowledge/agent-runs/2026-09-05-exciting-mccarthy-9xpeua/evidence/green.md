---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-9xpeua-evidence-green"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
goal_id: "2026-09-05-exciting-mccarthy-9xpeua-goal-copy-reference-action"
kind: "test_green"
reference: "web/src/lib/processoReference.ts + web/src/lib/processoReference.test.ts + web/src/components/ProcessoLookup.reference.test.ts"
summary: "After implementing buildProcessoReferenceText/buildDocumentoReferenceText and wiring 'Copiar referência' buttons into ProcessoLookup.svelte (dossier header + per-document, gated on doc.url), `npx vitest run src/lib/processoReference.test.ts src/components/ProcessoLookup.reference.test.ts src/components/ProcessoLookup.actions.test.ts src/components/ProcessoLookup.test.ts src/lib/processoCnj.test.ts` passed 97/97 tests. The full web suite (`npx vitest run`) passed 333/333 tests, and `npm run lint` (eslint) reported zero errors/warnings."
---

# Evidência GREEN

Implementação faz a suíte nova e toda a suíte web existente passarem, sem regressão de lint.

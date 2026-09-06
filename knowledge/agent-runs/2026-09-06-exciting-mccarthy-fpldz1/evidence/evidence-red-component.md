---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-fpldz1-evidence-red-component"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
goal_id: "2026-09-06-exciting-mccarthy-fpldz1-goal-continue-with-agent"
kind: "test_red"
reference: "web/src/components/ProcessoLookup.agentQuestion.test.ts, run via `npm test -- --run src/components/ProcessoLookup.agentQuestion.test.ts` before ProcessoLookup.svelte had the new button/link"
summary: "Wrote 3 tests against ProcessoLookup.svelte's found state before adding any production code: (1) clicking 'Continuar com um agente' copies a distinct, task-language question containing the exact consulted CNJ, and the same dossier's 'Copiar link'/'Copiar referência' still produce different text; (2) a secondary /agentes onboarding link exists and clicking the new action never triggers another buscarProcesso() call; (3) the button degrades gracefully (no lingering 'Pergunta copiada') when navigator.clipboard is undefined. All 3 failed naturally with `waitFor` timeouts because `getByText('Continuar com um agente')` never resolved — the button did not exist yet."
---

# Evidência RED — botão de continuidade no componente

Os três testes falharam por timeout de `waitFor` (botão inexistente) antes da alteração de `ProcessoLookup.svelte` — RED natural.

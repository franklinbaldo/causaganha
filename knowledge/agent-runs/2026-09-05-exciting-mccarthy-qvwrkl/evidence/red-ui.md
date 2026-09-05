---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-red-ui"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
kind: "test_red"
reference: "web/src/components/PublicationActions.reference.test.ts and web/src/components/PublicationCard.reference.test.ts, both run before the 'Copiar referência' button/wiring existed"
summary: "`npx vitest run src/components/PublicationActions.reference.test.ts` failed (button not found; 1/2 tests failing) before PublicationActions.svelte exposed onCopyReference/activeReferenceCopied, and `npx vitest run src/components/PublicationCard.reference.test.ts` failed 2/3 (only the no-link/no-button case trivially passed) before PublicationCard.svelte wired handleCopyReference — confirming both the component-level action and its plumbing into PublicationCard did not exist yet."
---

# Evidência RED — UI de /publicacoes

Testes escritos primeiro contra o botão/plumbing inexistente, confirmando falha antes da implementação.

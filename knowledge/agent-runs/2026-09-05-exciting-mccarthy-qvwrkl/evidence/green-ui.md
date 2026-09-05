---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-green-ui"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
kind: "test_green"
reference: "web/src/components/PublicationActions.svelte (new onCopyReference/activeReferenceCopied props + button gated on link), web/src/components/PublicationCard.svelte (handleCopyReference + currentPublicationUrl helper, threaded through PublicationResultItem.svelte and PublicationReader.svelte)"
summary: "`npx vitest run src/components/PublicationCard.reference.test.ts src/components/PublicationActions.reference.test.ts src/components/PublicationActions.dossier.test.ts src/lib/processoReference.test.ts` passes 15/15: the compact/reader/main PublicationActions call sites all receive the new props, clicking 'Copiar referência' on the main article view copies a buildDocumentoReferenceText-shaped block containing tribunal, tipo, data, the origin URL (ordered before the CausaGanha permalink) and, when present, the process number — never fabricated when absent — and the action disappears entirely when pub.link is missing, mirroring the existing 'Inteiro teor' gate."
---

# Evidência GREEN — UI de /publicacoes

Ação "Copiar referência" funcionando nas três variantes de card (compacto, leitor, principal), com contrato provado por teste em cada camada.

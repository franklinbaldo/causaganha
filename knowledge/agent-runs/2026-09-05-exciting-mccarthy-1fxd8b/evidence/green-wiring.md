---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-green-wiring"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "test_green"
reference: "web/src/components/ProcessoLookup.svelte — evidenceRows $derived + <ProcessoEvidenceMatrix rows={evidenceRows} /> placed between the existing snapshot section (#snapshot-title) and the avisos block"
summary: "Wired ProcessoEvidenceMatrix into ProcessoLookup.svelte: a new evidenceRows $derived computed from evidenceMatrixRows(processo.fontes, processo.avisos, processo.cobertura), rendered only inside the existing {#if status === 'found' && processo} branch, positioned after </section> closing .processo-dossie__snapshot and before the avisos {#if}. Both previously-red wiring tests now pass: the matrix heading renders after the snapshot heading and before the 'Fontes encontradas' heading (DOM-order assertion via compareDocumentPosition), and an avisos-flagged source renders 'Indisponível' distinctly from the 'Sem registro' ausente sources."
---

# GREEN: wiring ProcessoEvidenceMatrix into ProcessoLookup

`npx vitest run src/components/ProcessoLookup.evidenceMatrix.test.ts` → 2 passed.

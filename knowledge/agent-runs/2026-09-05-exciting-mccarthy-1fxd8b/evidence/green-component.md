---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-green-component"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "test_green"
reference: "web/src/components/ProcessoEvidenceMatrix.svelte"
summary: "Implemented the pure presentational component: takes rows: EvidenceMatrixRow[] as its only prop, renders one linked badge per row with papel/fonte/status as separate visible text spans (not color-only) and data-tone reusing the existing badge/data-tone CSS from base.css, with each row's href pointing at the source's existing detail-section id in ProcessoLookup.svelte (djen-title/datajud-title/documentos-title). All 4 previously-red tests now pass."
---

# GREEN: ProcessoEvidenceMatrix.svelte

`npx vitest run src/components/ProcessoEvidenceMatrix.reference.test.ts` → 4 passed.

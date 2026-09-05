---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-red-wiring"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "test_red"
reference: "web/src/components/ProcessoLookup.evidenceMatrix.test.ts (2 tests, written before wiring ProcessoEvidenceMatrix into ProcessoLookup.svelte)"
summary: "Both tests failed: waitFor(() => getByText('Resumo de evidências por fonte')) timed out because ProcessoLookup.svelte did not yet render the ProcessoEvidenceMatrix component for a found dossier — confirmed by the full DOM dump in the failure output showing the snapshot/fontes/datajud/djen/documentos sections with no evidence-matrix heading between them."
---

# RED: wiring ProcessoEvidenceMatrix into ProcessoLookup

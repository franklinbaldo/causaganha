---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-1fxd8b-check-vitest-red-wiring"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
command: "cd web && npx vitest run src/components/ProcessoLookup.evidenceMatrix.test.ts (before wiring ProcessoEvidenceMatrix into ProcessoLookup.svelte)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-red-wiring"
summary: "2/2 failed: waitFor(() => getByText('Resumo de evidências por fonte')) timed out, confirming the strip was not yet rendered anywhere in the found-dossier DOM."
---

# Check: vitest RED (wiring)

---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-qvwrkl-check-vitest-red-nullable"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
command: "cd web && npx vitest run src/lib/processoReference.test.ts (before widening DocumentoReferenceInput.nrProcessoMascara)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-red-nullable-process"
summary: "1/7 failed as intended: the new null-process-number test caught the literal 'do processo null' placeholder bug."
---

# Check: vitest RED (número de processo nulo)

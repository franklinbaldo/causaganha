---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-green-nullable-process"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
kind: "test_green"
reference: "web/src/lib/processoReference.ts (DocumentoReferenceInput.nrProcessoMascara widened to string | null, header line made conditional), web/src/lib/processoReference.test.ts"
summary: "`npx vitest run src/lib/processoReference.test.ts` passes 7/7 after widening the contract: the two pre-existing tests (which always pass a process number) are unmodified and still pass, and the new null-process-number test confirms no 'do processo' clause and no placeholder appear when the number is absent."
---

# Evidência GREEN — número de processo nulo

`buildDocumentoReferenceText` agora aceita `nrProcessoMascara: string | null` sem regressão nos testes existentes.

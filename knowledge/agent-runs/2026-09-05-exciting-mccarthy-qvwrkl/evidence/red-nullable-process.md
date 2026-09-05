---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-red-nullable-process"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
kind: "test_red"
reference: "web/src/lib/processoReference.test.ts, new test 'omits the process line ... when the record carries no process number', run before widening buildDocumentoReferenceText's contract"
summary: "`npx vitest run src/lib/processoReference.test.ts` failed 1/7: passing nrProcessoMascara: null produced the literal string 'do processo null' in the header line, confirming the exact placeholder-fabrication bug the widened contract needed to fix, before any implementation change."
---

# Evidência RED — número de processo nulo

Confirma que, antes da correção, `buildDocumentoReferenceText` produzia "do processo null" quando chamada sem número de processo — exatamente o defeito que o próximo passo corrige.

---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-qvwrkl-decision-nullable-process-number"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
question: "buildDocumentoReferenceText's DocumentoReferenceInput.nrProcessoMascara is required (string), but DjenPublication.numero_processo is optional — how should the builder behave for a /publicacoes result without a recognizable process number, without either crashing the gate or reusing a duplicate function?"
choice: "Widen DocumentoReferenceInput.nrProcessoMascara to string | null and make the header line's 'do processo X' clause conditional on it being present, instead of writing a second, near-duplicate builder for publications."
rationale: "The existing builder already encodes exactly the shape #1135 wants for a source+type+date+origin-URL+CausaGanha-URL reference; the only real gap was an assumption that does not hold for every DJEN publication. Widening the contract keeps one tested implementation reused by both /processo documents and /publicacoes results (matching the issue's own hint to reuse existing provenance components), and is strictly backward compatible: the two existing tests, which always pass a process number, keep passing unmodified. The alternative (a parallel buildPublicacaoReferenceText) would duplicate the same never-fabricate-a-field logic for no benefit."
---

# Decisão: número de processo nulável em buildDocumentoReferenceText

Amplia o contrato existente em vez de duplicar a função, mantendo a regra de nunca inventar um campo ausente também para o número de processo.

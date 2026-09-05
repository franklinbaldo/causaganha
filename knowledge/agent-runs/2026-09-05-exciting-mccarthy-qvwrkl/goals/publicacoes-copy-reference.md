---
type: AgentGoal
id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal: "Extend issue #1135's 'Copiar referência' action to /publicacoes: each publication result that carries a public origin URL (pub.link) gets a 'Copiar referência' button producing a short, stable, plain-text reference (fonte DJEN + tribunal when known, tipo, número de processo quando presente, data de disponibilização, URL de origem, e a URL da própria página do CausaGanha como contexto secundário), without inventing a process number when the publication does not carry one."
rationale: "The previous round's own next_move named this exact continuation, and #1135's acceptance criteria explicitly require the action on both /processo and /publicacoes results wherever provenance exists. The OKF reading found a concrete blocker: buildDocumentoReferenceText's contract requires a non-nullable process number, which real DJEN publications are not guaranteed to have — closing that gap is a prerequisite for reusing the existing, already-tested builder instead of duplicating it."
success_signal: "web/src/lib/processoReference.test.ts gains a passing test proving buildDocumentoReferenceText omits the process line (never a placeholder) when nrProcessoMascara is null, while its two existing tests (which always pass a process number) keep passing unmodified. PublicationActions.svelte exposes a 'Copiar referência' action gated on the same provenance condition as its existing 'Inteiro teor' link (pub.link present), and a new PublicationCard-level test proves clicking it copies text built from buildDocumentoReferenceText containing tribunal/tipo/data/url and the CausaGanha permalink, with the origin URL ordered before it. Full web vitest suite stays green and a PR is opened against main."
status: "achieved"
---

# Goal: ação "Copiar referência" em /publicacoes (issue #1135, segunda fatia)

Fecha o critério de aceite de #1135 ainda pendente ("resultados de /publicacoes onde houver provenance"), reaproveitando `buildDocumentoReferenceText` já testado, com um pequeno ajuste de contrato para admitir publicações sem número de processo reconhecido.

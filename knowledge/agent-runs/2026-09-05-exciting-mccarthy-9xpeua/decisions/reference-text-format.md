---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-9xpeua-decision-reference-text-format"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
goal_id: "2026-09-05-exciting-mccarthy-9xpeua-goal-copy-reference-action"
question: "What should the copied reference text contain, at which granularity, and which URL counts as 'origin' for the dossier level given /processo has no single per-CNJ source document?"
choice: "Two builders in a new web/src/lib/processoReference.ts: buildProcessoReferenceText() for the dossier header (process id, comma-joined present-source labels or an explicit 'nenhuma fonte' line, dataset freshness timestamp only when known, INDICE_PROCESSUAL_URL as the preserved origin artifact, and the current permalink as secondary CausaGanha context) and buildDocumentoReferenceText() for individual JURIS/STJ rows in the documentos timeline, gated on the row actually carrying a public url — no reference button is offered for a document without one."
rationale: "Issue #1135 explicitly forbids inventing absent fields (no hash/date placeholder) and requires the preserved/official origin to stay distinguishable from the CausaGanha URL. /processo has no single 'source record' — it is a reconciled index over 4 parquet sources — so indice_processual.parquet (already exported as INDICE_PROCESSUAL_URL in processoCnj.ts) is the only artifact that legitimately represents 'where this dossier's presence claim came from' at the header level; per-document references instead point at each document's own recorded url, which is a stronger, item-specific origin than the shared index. Gating the per-document button on doc.url!=null keeps the action's availability itself honest about provenance sufficiency, per the acceptance criteria's 'onde houver provenance'."
---

# Decisão: formato e granularidade da referência copiável

Duas funções puras, dois níveis de granularidade (dossiê e documento), URL de origem sempre antes da URL do CausaGanha no texto, e a ação só aparece quando a proveniência necessária existe de fato.

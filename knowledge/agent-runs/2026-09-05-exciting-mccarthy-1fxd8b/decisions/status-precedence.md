---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-1fxd8b-decision-status-precedence"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
question: "The dossier contract has no single per-source 'status' enum: presence comes from processo.fontes (a Fonte[] the CNJ was actually found in), unavailability comes from two separate, independently-populated signals (a per-CNJ query failure recorded as free text in processo.avisos, and a dataset-wide fetchCobertura() status of 'unavailable'). How should evidenceMatrixRows() reconcile these into one status per source, and which signal wins when a source is both absent from fontes and flagged unavailable by either signal?"
choice: "Compute status as: 'indisponivel' if either the per-CNJ avisos array contains an entry for that fonte or its FonteCobertura.status === 'unavailable'; otherwise 'presente' if included in fontes; otherwise 'ausente'. Indisponibilidade always takes precedence over ausência, never the reverse."
rationale: "A source that could not be queried has fontes.includes(fonte) === false today by construction (queryRowSafe returns null on failure, so the fonte is never added to processo.fontes) — so 'ausente' and 'indisponivel' overlap by construction for the avisos signal, and precedence is the only way to distinguish them for the exact case #1130's acceptance criteria demand ('ausência de CNJ é visualmente distinta de indisponibilidade'). Treating unavailability as the default and presence/absence as the fallback keeps the matrix a read of existing signals — no new query logic, no new field, no percentage or invented state, matching CLAUDE.md's and #1130's own explicit ban on inventing inferences in the visual component."
---

# Decisão: precedência indisponível > ausente em evidenceMatrixRows

Sem essa precedência explícita, uma fonte que falhou a consulta (avisos) seria indistinguível de uma fonte que legitimamente não tem registro para o CNJ — exatamente o critério de aceite que #1130 pede para diferenciar.

---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-silent-risk-staleness-ui"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
kind: "diff"
reference: "web/src/components/ProcessoLookup.svelte:17,79-84,390,431"
summary: "#924's 'risco silencioso' section suggested showing dataset_gerado_em's age as a visible warning on /processo when the fallback dataset gets stale, since the field already flows to the frontend but nothing displayed it. Live on main: ProcessoLookup.svelte imports `isDatasetStale` (line 17), derives `datasetStale` from `activeDatasetGeradoEm` via `isDatasetStale(activeDatasetGeradoEm, Date.now())` (line 84), and conditionally renders a warning block at two call sites (`{#if datasetStale}` at lines 390 and 431, covering both the 'found' and 'not_found' result paths). Already implemented."
---

# Evidência — "risco silencioso" (aviso de staleness em /processo) já implementado

`ProcessoLookup.svelte` já deriva e exibe `datasetStale` condicionalmente nos dois caminhos de resultado.

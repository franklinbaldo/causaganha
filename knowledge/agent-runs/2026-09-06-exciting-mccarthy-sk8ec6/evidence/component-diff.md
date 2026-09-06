---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-sk8ec6-evidence-component-diff"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
kind: "diff"
reference: "git diff web/src/components/DuckDBExplorer.svelte (74 insertions, 25 deletions)"
summary: "Extracted the Internet Archive metadata probe into a pure-ish checkDataset(id) helper returning {status, files, error, cacheable}: 404 or empty-Parquet-list → missing/cacheable; rejected fetch, non-ok non-404 response, JSON-parse failure, or unexpected body shape → unavailable/not-cacheable. The dataset-validation $effect now only caches results where cacheable is true, and tracks a new retryNonce $state so a 'Tentar verificar novamente' button (rendered in a new datasetStatus === 'unavailable' branch, alongside the existing 'missing' alert) can force a fresh probe by deleting the itemId's cache entry and bumping retryNonce, without touching selectedTribunal/selectedYear/sql. runQuery() gained a matching early-return for datasetStatus === 'unavailable', defensively mirroring the existing 'missing' guard (the Executar button and SQL textarea were already disabled for any non-'ready' status). describeUnavailableDataset() adds a message distinct from describeMissingDataset(), explicitly framing the failure as Internet Archive instability rather than dataset absence."
---

# Evidência: diff do componente

`checkDataset()` extrai a classificação missing/unavailable; cache só grava resultados `cacheable`; novo botão de retry via `retryNonce`; `runQuery()` ganha guarda espelhada para `unavailable`; nova mensagem `describeUnavailableDataset()`.

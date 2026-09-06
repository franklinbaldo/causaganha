---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-sk8ec6-evidence-green-tests"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
kind: "test_green"
reference: "npx vitest run src/components/DuckDBExplorer.dataset-availability.test.ts --reporter=verbose (post-fix)"
summary: "All 6 tests pass after implementing the checkDataset() classification helper, the 'unavailable' UI branch, and the retryDatasetCheck() action in DuckDBExplorer.svelte: (1) 404 → missing; (2) valid metadata, no parquet → missing; (3) 503 → unavailable, distinct message, no 'missing' text, retry button present; (4) rejected fetch (TypeError) → unavailable, no 'missing' text; (5) transient 503 followed by a successful retry reaches 'ready' with exactly 2 fetch calls total, proving the transient failure was not cached; (6) tribunal/year selection values remain 'TJRO'/current year after an 'unavailable' classification."
---

# Evidência: testes GREEN

Todos os 6 testes passam após a implementação de `checkDataset()`, do estado visual `unavailable` e do botão de retry `retryDatasetCheck()` em `DuckDBExplorer.svelte`.

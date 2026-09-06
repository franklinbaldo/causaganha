---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-yigsua-evidence-component-diff"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
goal_id: "2026-09-06-exciting-mccarthy-yigsua-goal-fix-1197-query-error-classification"
kind: "diff"
reference: "git diff web/src/components/DuckDBExplorer.svelte"
summary: "Adds a pure classifyQueryError(message, id) helper (returns 'missing'/'unavailable'/null per the decision-classification-heuristic rationale) and replaces runQuery()'s single-line `message.includes(itemId) || message.includes('HTTP')` ternary with a three-way branch that decorates the original error with describeMissingDataset() only for 'missing', with describeUnavailableDataset() (already used by #1193's dataset-check UI) for 'unavailable', and leaves any other message (local SQL/DuckDB errors) untouched. No other function, state variable, or template block changed; retry is the existing 'Executar' button (no caching exists in runQuery(), so no new caching bug to introduce)."
---

# Evidência — diff do componente (#1197)

`classifyQueryError()` + reescrita do `catch` de `runQuery()`. Sem outras mudanças de estado ou template.

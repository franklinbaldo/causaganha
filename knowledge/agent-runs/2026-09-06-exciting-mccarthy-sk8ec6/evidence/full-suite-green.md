---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-sk8ec6-evidence-full-suite-green"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
kind: "ci"
reference: "npx vitest run (web/), uv run ruff check, uv run ruff format --check (repo root)"
summary: "Full web test suite: 53 test files, 424 tests, all passing after the DuckDBExplorer.svelte fix and its new test file — no regressions in any other component. Python gates unaffected (no .py files changed this round): ruff check reports 'All checks passed!', ruff format --check reports '378 files already formatted'. `npx astro check` reports the same 19 pre-existing type errors as an unmodified checkout of main (verified via `git stash` / `git stash pop` before and after the change) — all in unrelated files (ProcessoLookup.reference.test.ts, PublicationActions.reference.test.ts, renderedContracts.integration.test.ts, two .astro redirect stubs), none mentioning DuckDBExplorer."
---

# Evidência: suíte completa verde

`vitest run`: 424/424 testes passando (53 arquivos). `ruff check`/`ruff format --check`: sem alterações Python nesta rodada, ambos verdes. `astro check`: mesmos 19 erros pré-existentes de `main` (confirmado via `git stash`), nenhum relacionado a `DuckDBExplorer`.

---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-e0vvbh-evidence-full-suites-green"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
goal_id: "2026-09-25-exciting-mccarthy-e0vvbh-goal-tribunal-coerente-manifesto"
kind: "ci"
reference: "uv run pytest -q (repositório inteiro); cd web && npx vitest run; uv run ruff check/format --check; cd web && npx eslint .; cd web && npx astro check"
summary: "`uv run pytest -q` sobre o repositório inteiro terminou com exit code 0 (suíte completa verde, nenhuma regressão introduzida pela mudança em service.py). `cd web && npx vitest run`: 75 arquivos, 560 testes, 100% verde. `uv run ruff check` e `uv run ruff format --check`: sem violações no repositório inteiro. `npx eslint .`: 0 erros (43 warnings pré-existentes em arquivos gerados `styled-system/*.d.ts`, não tocados nesta rodada). `npx astro check`: 0 erros, 0 warnings, 5 hints pré-existentes em arquivos não tocados (152 arquivos)."
---

# Evidência: suítes completas verdes após a mudança

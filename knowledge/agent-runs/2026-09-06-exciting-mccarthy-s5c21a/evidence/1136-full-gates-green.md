---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-s5c21a-evidence-1136-full-gates-green"
run_id: "2026-09-06-exciting-mccarthy-s5c21a"
goal_id: "2026-09-06-exciting-mccarthy-s5c21a-goal-1136-minhas-consultas-query-states"
kind: "runtime"
reference: "npx vitest run; npm run typecheck; npx eslint .; npm run build (web/); uv run ruff check; uv run ruff format --check; uv run pytest -q (repo root)"
summary: "Full web vitest suite: 45 test files, 370 tests, all passed. `npm run typecheck`: 19 pre-existing errors, identical count and files to the pre-change baseline recorded by the prior round (6tcxrn) — none introduced by this CSS-only change. `npx eslint .`: 0 errors, 43 pre-existing warnings confined to generated styled-system/*.d.ts files. `npm run build` (after `uv run python scripts/render_queries.py` populated the gitignored web/public/data/*.json contracts this sandbox needed locally): 120 pages built successfully, no errors. `uv run ruff check`: all checks passed. `uv run ruff format --check`: 378 files already formatted. `uv run pytest -q`: full Python suite green except the expected, self-referential test_check_agent_run_completeness failure for this round's own in-progress report, resolved by this round's own final commit once completed_at/result_summary/etc. are filled in, per the scaffold's own documented rule."
---

# Evidência — gates completos verdes

Nenhuma regressão introduzida: mudança restrita a CSS (seletores) e a um arquivo de teste. Typecheck com a mesma contagem de erros pré-existentes da rodada anterior; eslint sem erros; build estático completo; ruff/pytest do backend Python inalterados e verdes.

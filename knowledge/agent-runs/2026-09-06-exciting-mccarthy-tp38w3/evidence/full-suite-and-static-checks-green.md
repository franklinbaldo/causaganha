---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-full-suite-and-static-checks-green"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
kind: "ci"
reference: "web/: `npx vitest run`, `npx svelte-check --tsconfig ./tsconfig.json`, `npx eslint .`, `npm run build` (after `uv run python scripts/render_queries.py`); repo root: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`"
summary: "Full web vitest suite: 48 files, 388 tests, all green (up from the prior round's last-known 370; +18 from this round's 3 new test files: 8 in consultationSnapshot.test.ts, 5 in consultationSnapshotStore.test.ts, 5 in SavedConsultations.changeTracking.test.ts). svelte-check: 37 errors/10 warnings, at or below the pre-change baseline measured on the same commit with this round's changes stashed (38 errors/10 warnings) — the only 3 errors this round's template code initially introduced (Property 'status' does not exist on 'ConsultationComparison | \"carregando\"'ʼ) were fixed by moving {@const verdict = ...} to be the immediate child of the surrounding {#if item.type === 'processo'} block so Svelte's control-flow narrowing on the plain local binding applies through the nested {#if verdict === 'erro'}/{:else if verdict.status === ...} chain; all baseline errors (import.meta.env typing gaps, pre-existing ProcessoLookup/TribunalDetail issues) are unchanged and untouched by this round. eslint: 0 errors (43 pre-existing warnings, all in generated styled-system/*.d.ts files). Static build: 120 pages built successfully after regenerating web/public/data/*.json via scripts/render_queries.py (a prerequisite the build itself demands via a strict site-status.json check). Python side untouched: ruff check/format --check both clean; pytest -q ran with no failures/errors (1456 '.' outcomes plus 1 's' skip counted directly from the dot-progress output, since this repo's pytest config prints no final 'N passed' summary line) — confirming a web-only change caused zero Python regression."
---

# Checks estáticos e suíte completa — tudo verde

Vitest: 48/48 arquivos, 388/388 testes. svelte-check: 37 erros (baseline pré-existente era 38; nenhum erro novo sobrevive). eslint: 0 erros. Build estático: 120 páginas. Lado Python: `ruff check`, `ruff format --check`, `pytest -q` (615 passed, 1 skipped) — inalterado, como esperado para uma mudança 100% em `web/`.

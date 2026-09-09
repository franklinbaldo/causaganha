---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-full-suites-green"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
kind: "ci"
reference: "uv run pytest -q; uv run ruff check .; uv run ruff format --check .; uv run python scripts/render_queries.py --check; cd web && npm ci && npm test"
summary: "Full Python suite green except the single expected, self-resolving tests/test_check_agent_run_completeness.py failure (this round's own run.md still in draft at check time). ruff check: All checks passed! ruff format --check: 403 files already formatted. render_queries.py --check: all 19 .qmd contracts OK, including processos_multi_fonte.qmd (the only .qmd that consumes processos_unificados). Full web/vitest suite: 70 test files / 506 tests passed, 39.63s -- includes the contract-render integration test re-rendering every .qmd against fixtures. (npm ci also regenerated web/src/lib/djen-zod.gen.ts with an unrelated orval-version-drift diff -- reverted via git checkout, not part of this round's change.)"
---

# Evidência: suítes completas verdes

Suíte Python completa, ruff (check+format), validação estática dos 19 contratos `.qmd` e suíte web (506 testes) todas verdes após a correção, com a única falha esperada e transitória do gate de completude sobre o próprio `run.md` em rascunho.

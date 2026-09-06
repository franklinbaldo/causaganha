---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-3kjpfr-evidence-full-suite-and-build-with-real-data"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
goal_id: "2026-09-06-exciting-mccarthy-3kjpfr-goal-drilldown-cobertura-por-tribunal"
kind: "runtime"
reference: "npm run test (405 tests / 50 files), npm run lint (0 errors), npm run typecheck (19 errors — identical to the pre-change baseline measured with these files stashed), npm run build (120 pages) after `uv run python scripts/render_queries.py` regenerated real production contract JSON"
summary: "Full web suite green: 405/405 tests across 50 files (+17 tests, +2 files vs. before this round). eslint: 0 errors. svelte-check: 19 errors both with and without this round's files present (stashed comparison), so zero new type errors introduced. Static build succeeded (120 pages including /stats.html with the new section and its astro-island). Verified against real production data, not just fixtures: after regenerating web/public/data/*.json from the live manifest, inspected tribunal_coverage.json (96 tribunals) and tribunal_calendar.json (13.9MB, real per-day rows) directly — the explorer's default view (first tribunal alphabetically, CJF, last-30-days window ending at the real site-status generated_at of 2026-09-06T06:36:39Z) has 20 real observed days in range, confirming the default /stats view shows real coverage numbers rather than immediately falling into the 'sem evidência suficiente' branch. web/src/lib/djen-zod.gen.ts churned on every codegen run (orval version drift between the lockfile-pinned version and what actually resolved in this environment, unrelated to this round's change) and was reverted with `git checkout --` before each check to keep the diff scoped to #1131."
---

# Evidência: suíte completa, build estático e validação contra dado real de produção

405/405 testes, 0 erros de lint, typecheck sem regressão (19 erros antes e depois, comparado com stash), build de 120 páginas com dado real de produção regenerado via `render_queries.py` — o recorte padrão do explorador (CJF, últimos 30 dias) tem 20 dias observados reais, confirmando que a integração funciona com o manifesto real, não só com fixtures de teste.

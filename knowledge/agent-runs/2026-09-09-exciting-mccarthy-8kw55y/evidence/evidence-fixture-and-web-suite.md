---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-fixture-and-web-suite"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
goal_id: "2026-09-09-exciting-mccarthy-8kw55y-goal-lawyer-ratings-ia-fallback"
kind: "runtime"
reference: "scripts/render_contract_fixture.py; web/src/lib/data/renderedContracts.integration.test.ts; full web/vitest suite"
summary: "Verified scripts/render_contract_fixture.py needed no change: it already patches renderer.DEV_RATINGS_DIR to a fixtures dir containing real local lawyer_ratings.parquet/ratings_history.parquet files (written by _write_fixtures from _synthetic_lawyer_ratings/_synthetic_ratings_history), so the new IA-fallback branch this round added is never reached in the fixture harness -- the local-file-exists check short-circuits first, exactly like it already did for _register_acordaos's _STJ_PARQUET fixture path. Confirmed via `uv run python scripts/render_contract_fixture.py /tmp/fixture-check` (completes in <1s, no network, all .qmd render including lawyer_leaderboard.qmd) and, after `npm ci` (node_modules was absent in this sandbox), `npm run test -- src/lib/data/renderedContracts.integration.test.ts` (1 passed, 1.66s) and the full `npm run test` (70 files / 506 tests passed, 31.64s -- same baseline as the last two rounds, pf1xhn/0lpi0s)."
---

# Fixture e suíte web

Confirmado que `render_contract_fixture.py` não precisa de patch adicional (o `DEV_RATINGS_DIR` já aponta para arquivos locais reais no fixture), e que a suíte web completa permanece verde (70/506).

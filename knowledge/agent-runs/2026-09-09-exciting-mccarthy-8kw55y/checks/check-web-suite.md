---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-8kw55y-check-web-suite"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
command: "npm ci (node_modules was absent in this sandbox) then npm run test -- src/lib/data/renderedContracts.integration.test.ts, then npm run test (full suite), from web/"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-fixture-and-web-suite"
summary: "Targeted integration test: 1 passed (1), 1.66s, no real network. Full suite: 70 files / 506 tests passed, 31.64s -- matches the last two rounds' baseline exactly, confirming render_contract_fixture.py's existing DEV_RATINGS_DIR patch already isolates the new IA-fallback branch this round added."
---

# Check: suíte web/vitest completa

70/506 verde, mesmo baseline das duas últimas rodadas.

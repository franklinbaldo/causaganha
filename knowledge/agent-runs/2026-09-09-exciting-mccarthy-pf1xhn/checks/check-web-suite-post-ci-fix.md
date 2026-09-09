---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-pf1xhn-check-web-suite-post-ci-fix"
run_id: "2026-09-09-exciting-mccarthy-pf1xhn"
goal_id: "2026-09-09-exciting-mccarthy-pf1xhn-goal-juris-datajud-ia-fallback"
command: "cd web && npm ci && npx vitest run src/lib/data/renderedContracts.integration.test.ts && npx vitest run"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-pf1xhn-evidence-ci-fix-fixture-network-isolation"
summary: "Reproduced PR #1356's CI failure locally (npm ci then vitest run on the timing-out test), confirmed it now passes in 2.15s after the render_contract_fixture.py network-isolation fix, then ran the full web suite: 70 files / 506 tests, all green."
---

# Check: suíte web após correção do CI

`npm ci` seguido de `npx vitest run` no teste que travava e depois na suíte completa. Teste de integração volta a passar em 2.15s (antes: timeout em 120s+). Suíte web completa: 70 arquivos / 506 testes, todos verdes.

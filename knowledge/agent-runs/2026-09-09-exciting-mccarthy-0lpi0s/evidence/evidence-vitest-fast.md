---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-vitest-fast"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
kind: "runtime"
reference: "cd web && npx vitest run src/lib/data/renderedContracts.integration.test.ts; cd web && npx vitest run (full suite)"
summary: "The exact integration test that timed out at 120s in the previous round's incident (renderedContracts.integration.test.ts) now completes in 1.41s, with the network guard active throughout render_fixture()'s render_all() call. Full web suite: 70 test files / 506 tests, all passed, 26.57s total -- no regression from the patch/restore unification (web/src/lib/data/contracts.ts consumers, tribunal_calendar partitioning, and every other .qmd-backed frontend schema all still validate against the fixture output)."
---

# Evidência: teste de integração do frontend rápido e verde

O teste que travava em 120s na rodada anterior agora completa em 1.41s com a guarda de rede ativa. Suíte web completa: 70 arquivos / 506 testes, todos verdes.

---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-0lpi0s-check-web-suite"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
command: "cd web && npx vitest run src/lib/data/renderedContracts.integration.test.ts; cd web && npx vitest run"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-vitest-fast"
summary: "Targeted integration test: 1 passed, 1.41s (previously timed out at 120s in the incident this goal follows up on). Full web suite: 70 files / 506 tests, all passed, 26.57s."
---

# Check: suíte web (vitest)

Teste de integração alvo: 1 aprovado em 1.41s. Suíte web completa: 70 arquivos / 506 testes, todos aprovados.

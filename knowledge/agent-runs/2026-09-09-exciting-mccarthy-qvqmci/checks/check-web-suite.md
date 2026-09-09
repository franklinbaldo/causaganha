---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qvqmci-check-web-suite"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
command: "cd web && npm ci && npm test"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-qvqmci-evidence-web-suite"
summary: "Test Files 70 passed (70), Tests 506 passed (506), 34.07s. Includes the full contract-render integration test (render_queries.py --strict against fixtures for every .qmd, schema-validated) -- zero failures, network-isolated per the guard added by round 0lpi0s."
---

# Check: suíte web (vitest)

70 arquivos de teste, 506 testes, todos verdes -- incluindo o suite de integração de contratos renderizados.

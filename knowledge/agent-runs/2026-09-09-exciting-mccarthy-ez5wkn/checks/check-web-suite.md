---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ez5wkn-check-web-suite"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
command: "cd web && npm ci && npm test"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-full-suites-green"
summary: "Test Files 70 passed (70), Tests 506 passed (506), 39.63s. Includes the full contract-render integration test (render_queries.py --strict against fixtures for every .qmd, schema-validated). npm ci's codegen step also touched web/src/lib/djen-zod.gen.ts with an unrelated orval-version-drift diff, reverted via git checkout -- not part of this round's change."
---

# Check: suíte web (vitest)

70 arquivos de teste, 506 testes, todos verdes -- incluindo o suite de integração de contratos renderizados.

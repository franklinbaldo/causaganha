---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-e0vvbh-check-web-parity-and-suite"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
goal_id: "2026-09-25-exciting-mccarthy-e0vvbh-goal-tribunal-coerente-manifesto"
command: "cd web && npx vitest run src/lib/processoQueryPlanParity.test.ts && npx vitest run && npx eslint . && npx astro check"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-e0vvbh-evidence-full-suites-green"
summary: "Harness de paridade de plano de consulta (#1107) continua 4/4 verde após buildIndiceSql passar a selecionar tribunal -- sem divergência entre python_rows e web_rows. Suíte web completa: 75 arquivos/560 testes verde. eslint: 0 erros. astro check: 0 erros/0 warnings."
---

# Check: paridade Web e suíte web completa

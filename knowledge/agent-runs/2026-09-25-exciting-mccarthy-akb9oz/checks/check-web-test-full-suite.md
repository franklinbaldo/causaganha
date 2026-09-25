---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-web-test-full-suite"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "cd web && npx vitest run"
result: "passed"
summary: "79 arquivos, 585 testes, 100% verde -- nenhuma regressao nos 583 testes pre-existentes; os 2 a mais vem dos casos novos de Layout.csp.test.ts (verificacao das 3 paginas com CSP) e htmlSinks.inventory.test.ts alem dos ja contados na primeira rodada RED (a contagem de testes novos totais e 25 distribuidos em 4 arquivos: Layout.csp.test.ts, htmlSinks.inventory.test.ts, djenXssCorpus.test.ts, redirectStubs.noInlineScript.test.ts)."
---

# Check: suite Vitest completa (web), final

```
$ cd web && npx vitest run
 Test Files  79 passed (79)
      Tests  585 passed (585)
```

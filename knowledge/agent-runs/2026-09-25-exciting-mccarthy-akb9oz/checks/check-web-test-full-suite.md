---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-web-test-full-suite"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "cd web && npx vitest run"
result: "passed"
summary: "80 arquivos, 595 testes, 100% verde -- nenhuma regressao nos 583 testes pre-existentes ao inicio da rodada. Os 12 a mais vem de 5 arquivos de teste novos: Layout.csp.test.ts, htmlSinks.inventory.test.ts, djenXssCorpus.test.ts, _redirectStubs.noInlineScript.test.ts (25 testes, adicionados no trabalho principal de #1613) e injectCspHashes.test.ts (10 testes, adicionado ao corrigir o fix de hash allowlisting apos compare-product-surfaces revelar que a CSP bloqueava a hidratacao real do Astro -- ver decision-csp-hash-not-unsafe-inline)."
---

# Check: suite Vitest completa (web), final

```
$ cd web && npx vitest run
 Test Files  80 passed (80)
      Tests  595 passed (595)
```

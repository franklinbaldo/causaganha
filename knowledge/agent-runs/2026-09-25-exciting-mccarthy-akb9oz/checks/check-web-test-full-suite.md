---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-web-test-full-suite"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "cd web && npx vitest run"
result: "passed"
summary: "80 arquivos, 601 testes, 100% verde -- nenhuma regressao nos 583 testes pre-existentes ao inicio da rodada. Os 18 a mais vem de 5 arquivos de teste novos (Layout.csp.test.ts, htmlSinks.inventory.test.ts, djenXssCorpus.test.ts, _redirectStubs.noInlineScript.test.ts, injectCspHashes.test.ts -- 25+15 testes, trabalho principal de #1613 e os fixes sucessivos de CSP/CodeQL, ver decision-csp-hash-not-unsafe-inline e evidence-codeql-fix-script-closing-tag-regex) mais 1 teste novo em ProcessoLookup.test.ts (regressao para o bug de onMount bloqueando a validacao de CNJ na inicializacao do DuckDB-WASM, ver decision-decouple-cnj-validation-from-duckdb-init)."
---

# Check: suite Vitest completa (web), final

```
$ cd web && npx vitest run
 Test Files  80 passed (80)
      Tests  601 passed (601)
```

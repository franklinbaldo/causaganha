---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r2xele-check-web-test-full-suite"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
command: "cd web && npx vitest run"
result: "passed"
summary: "Suite Vitest completa do frontend (75 arquivos de teste, 560 testes) verde apos a mudanca em processoCnj.ts/processoCnj.test.ts -- nenhuma regressao em nenhum outro modulo, incluindo os testes de ProcessoLookup.svelte e a suite de paridade de plano de consulta (processoQueryPlanParity.test.ts) que tambem exercitam buscarProcesso indiretamente."
---

# Check: suite Vitest completa (web)

```
$ npx vitest run
 Test Files  75 passed (75)
      Tests  560 passed (560)
   Duration  34.39s
```

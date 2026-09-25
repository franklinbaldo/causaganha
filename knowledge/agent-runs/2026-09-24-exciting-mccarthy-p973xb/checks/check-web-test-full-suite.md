---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-p973xb-check-web-test-full-suite"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
command: "cd web && npm run test"
result: "passed"
summary: "75 arquivos de teste, 547 testes, 100% verdes apos a correcao de csvField(). Uma primeira execucao teve 1 suite falhando por timeout de hook (src/lib/processoQueryPlanParity.test.ts, que invoca 'uv run python ...') -- reproduzido isoladamente com timeout maior e confirmado como aquecimento lento do ambiente uv desta sandbox (primeira invocacao de 'uv' no processo), nao uma regressao desta mudanca: a segunda execucao completa da suite ficou 100% verde sem qualquer alteracao de codigo."
---

# Check: suite completa de testes do web apos a correcao de #1612

```
$ npm run test
 Test Files  75 passed (75)
      Tests  547 passed (547)
```

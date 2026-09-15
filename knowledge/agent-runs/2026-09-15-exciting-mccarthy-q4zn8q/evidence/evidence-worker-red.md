---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-q4zn8q-evidence-worker-red"
run_id: "2026-09-15-exciting-mccarthy-q4zn8q"
goal_id: "2026-09-15-exciting-mccarthy-q4zn8q-goal-archive-cors-proxy"
kind: "test_red"
reference: "deployment/archive-cors-proxy/test/index.test.js contra um src/index.js stub (fetch() => 501, sem parseDownloadPath nem handleRequest exportados)"
summary: "npx vitest run: 15/15 testes falhando (TypeError: handleRequest is not a function / parseDownloadPath is not a function) contra o stub, confirmando RED real antes da implementacao do Worker."
---

# Evidencia: RED real do proxy CORS

`deployment/archive-cors-proxy/test/index.test.js` foi escrito primeiro,
contra o Worker completo planejado. Para confirmar RED real (nao apenas
assumido), `src/index.js` foi temporariamente substituido por um stub sem
`parseDownloadPath`/`handleRequest` exportados antes de rodar
`npx vitest run`:

```
 Test Files  1 failed (1)
      Tests  15 failed (15)
```

Todos os 15 casos falharam com `TypeError: handleRequest is not a
function` ou `parseDownloadPath is not a function`, confirmando que os
testes exercitam de fato o contrato do Worker (allowlist de path, CORS
preflight, forwarding de Range, erro 502) e nao passam trivialmente.

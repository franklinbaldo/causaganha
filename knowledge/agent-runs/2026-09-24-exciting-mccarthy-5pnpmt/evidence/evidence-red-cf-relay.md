---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-red-cf-relay"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
kind: "test_red"
reference: "deployment/relay-cf/test/index.test.js (9 novos casos adicionados nesta rodada, rodando sob @cloudflare/vitest-pool-workers/workerd real)"
summary: "npm test contra o deployment/relay-cf/src/index.js original: 7 dos 18 casos falharam, confirmando RED. Falhas: 'never forwards Authorization or Cookie to upstream' (502 em vez de 200 -- o mock de fetchImpl assertava init.headers.has('authorization')===false e falhava, provando que Authorization/Cookie eram encaminhados); 'strips Set-Cookie from the upstream response' (Set-Cookie da resposta volta ao chamador); 'readBounded assembles chunks...'/'readBounded returns null...'/'readBounded returns an empty buffer...' (3 casos -- TypeError: readBounded is not a function, funcao nao existia); 'rejects a request body over budget with 413...' (502 em vez de 413, nenhum limite aplicado); 'returns 502 when the upstream response exceeds budget' (200 em vez de 502, resposta upstream sempre repassada sem limite)."
---

# Evidencia RED: relay Cloudflare sem politica de egress (TM-02/#1609)

```
$ npm test
Test Files  1 failed (1)
     Tests  7 failed | 11 passed (18)
```

Confirma ao vivo, antes de qualquer mudanca de producao, que o relay
Cloudflare (`deployment/relay-cf/src/index.js`) — apesar de ja ser
HTTPS-only e GET/HEAD/POST-only — encaminhava `Authorization`/`Cookie`
ao upstream, devolvia `Set-Cookie` ao chamador, e nao tinha nenhum
teto de tamanho de corpo de requisicao ou resposta.

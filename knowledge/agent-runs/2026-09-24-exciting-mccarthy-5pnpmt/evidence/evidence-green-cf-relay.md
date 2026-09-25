---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-green-cf-relay"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
kind: "test_green"
reference: "deployment/relay-cf/src/index.js; deployment/relay-cf/test/index.test.js"
summary: "npm test: 18 passed apos a correcao. index.js agora: remove authorization/cookie de STRIP_REQUEST_HEADERS e set-cookie de STRIP_RESPONSE_HEADERS; le corpo de requisicao e resposta via readBounded() (nova funcao exportada) ate MAX_REQUEST_BODY_BYTES=10MiB/MAX_RESPONSE_BYTES=25MiB, retornando null (413 para requisicao, 502 para resposta) se excedido em vez de materializar sem limite; handleRequest ganhou um 4o parametro opcional 'limits' (mesmo padrao de injecao de dependencia ja usado para fetchImpl) para permitir testar os limites com valores pequenos sem alocar payloads multi-MB reais."
---

# Evidencia GREEN: relay Cloudflare com politica de egress (TM-02/#1609)

```
$ npm test
Test Files  1 passed (1)
     Tests  18 passed (18)
```

Tambem confirmado: `npm run check` (`wrangler deploy --dry-run`) builda
sem erro (Total Upload: 5.42 KiB / gzip: 1.85 KiB, No bindings found).
`deployment/relay-cf/package-lock.json` foi revertido apos `npm
install` (churn de metadata `libc` nao relacionado a esta mudanca,
vindo de uma versao de npm diferente da que gerou o lockfile
commitado) para manter o diff desta rodada focado no essencial.

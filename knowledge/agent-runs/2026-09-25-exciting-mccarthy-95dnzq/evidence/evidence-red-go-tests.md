---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-95dnzq-evidence-red-go-tests"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal_id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
kind: "test_red"
reference: "deployment/djen_proxy_test.go rodado com `go test ./...` contra o conteudo original (pre-fix) de deployment/djen_proxy.go, antes de qualquer mudanca de producao"
summary: "RED confirmado ao vivo: TestAllowed falhou para /comunicacao, /swagger/index.html e /login (allowed() retornava true para os 3 -- o proprio 'allowed' do codigo original os aceitava, nao so a rota /api/). TestSecurityRejectsMutatingMethods falhou para POST/PUT/DELETE/PATCH/OPTIONS numa rota permitida (todos retornaram 200 -- log real 'ALLOWED: /api/v1/comunicacao' antes do handler downstream rodar, provando que nao havia nenhuma checagem de metodo). TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao falhou para os 3 paths (200 em vez de 403). TestSecurityRejectsMutatingMethodEvenOffWhitelist falhou (POST /login retornou 200 em vez de 405). Unico teste que ja passava antes da correcao: TestSecurityAllowsGetOnWhitelistedPath (GET numa rota /api/ ja funcionava, como esperado -- o bug era so permissividade excessiva, nunca falta de acesso ao caminho legitimo)."
---

# Evidencia: RED ao vivo contra djen_proxy.go original

```
$ cd deployment && go test ./... -v
=== RUN   TestAllowed
    djen_proxy_test.go:28: allowed("/comunicacao") = true, want false
    djen_proxy_test.go:28: allowed("/swagger/index.html") = true, want false
    djen_proxy_test.go:28: allowed("/login") = true, want false
--- FAIL: TestAllowed (0.00s)
=== RUN   TestSecurityRejectsMutatingMethods
2026/09/25 02:29:52 ✅ ALLOWED: /api/v1/comunicacao
    djen_proxy_test.go:44: method POST on whitelisted path: got status 200, want 405
    djen_proxy_test.go:44: method PUT on whitelisted path: got status 200, want 405
    djen_proxy_test.go:44: method DELETE on whitelisted path: got status 200, want 405
    djen_proxy_test.go:44: method PATCH on whitelisted path: got status 200, want 405
    djen_proxy_test.go:44: method OPTIONS on whitelisted path: got status 200, want 405
--- FAIL: TestSecurityRejectsMutatingMethods (0.00s)
=== RUN   TestSecurityAllowsGetOnWhitelistedPath
--- PASS: TestSecurityAllowsGetOnWhitelistedPath (0.00s)
=== RUN   TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao
    djen_proxy_test.go:77: GET /login: got status 200, want 403
    djen_proxy_test.go:77: GET /swagger/index.html: got status 200, want 403
    djen_proxy_test.go:77: GET /comunicacao: got status 200, want 403
--- FAIL: TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao (0.00s)
=== RUN   TestSecurityRejectsMutatingMethodEvenOffWhitelist
    djen_proxy_test.go:94: POST /login: got status 200, want 405
--- FAIL: TestSecurityRejectsMutatingMethodEvenOffWhitelist (0.00s)
FAIL
FAIL	github.com/franklinbaldo/causaganha/deployment	0.006s
```

4 de 5 testes falharam contra o codigo real, antes de qualquer mudanca
de producao -- confirma a vulnerabilidade descrita em TM-02/#1609 de
forma reproduzivel, nao so por leitura do codigo.

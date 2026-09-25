---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-95dnzq-evidence-green-go-tests"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal_id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
kind: "test_green"
reference: "deployment/djen_proxy_test.go rodado com `go test ./...`, `go vet ./...` e `go build ./...` apos a correcao de deployment/djen_proxy.go (WHITELIST=[\"/api/\"], ALLOWED_METHODS={GET})"
summary: "GREEN: 5/5 testes passam (TestAllowed, TestSecurityRejectsMutatingMethods, TestSecurityAllowsGetOnWhitelistedPath, TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao, TestSecurityRejectsMutatingMethodEvenOffWhitelist). go vet ./... e go build ./... sem erros. Logs de execucao confirmam o comportamento correto: '🚨 BLOCKED METHOD' para os 5 metodos mutantes testados, '🚨 BLOCKED' para /login, /swagger/index.html e /comunicacao, '✅ ALLOWED' apenas para GET /api/v1/comunicacao."
---

# Evidencia: GREEN apos a correcao

```
$ cd deployment && go vet ./... && go build ./... && go test ./... -v
=== RUN   TestAllowed
--- PASS: TestAllowed (0.00s)
=== RUN   TestSecurityRejectsMutatingMethods
2026/09/25 02:30:15 🚨 BLOCKED METHOD: POST /api/v1/comunicacao
2026/09/25 02:30:15 🚨 BLOCKED METHOD: PUT /api/v1/comunicacao
2026/09/25 02:30:15 🚨 BLOCKED METHOD: DELETE /api/v1/comunicacao
2026/09/25 02:30:15 🚨 BLOCKED METHOD: PATCH /api/v1/comunicacao
2026/09/25 02:30:15 🚨 BLOCKED METHOD: OPTIONS /api/v1/comunicacao
--- PASS: TestSecurityRejectsMutatingMethods (0.00s)
=== RUN   TestSecurityAllowsGetOnWhitelistedPath
2026/09/25 02:30:15 ✅ ALLOWED: /api/v1/comunicacao
--- PASS: TestSecurityAllowsGetOnWhitelistedPath (0.00s)
=== RUN   TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao
2026/09/25 02:30:15 🚨 BLOCKED: /login
2026/09/25 02:30:15 🚨 BLOCKED: /swagger/index.html
2026/09/25 02:30:15 🚨 BLOCKED: /comunicacao
--- PASS: TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao (0.00s)
=== RUN   TestSecurityRejectsMutatingMethodEvenOffWhitelist
2026/09/25 02:30:15 🚨 BLOCKED METHOD: POST /login
--- PASS: TestSecurityRejectsMutatingMethodEvenOffWhitelist (0.00s)
PASS
ok  	github.com/franklinbaldo/causaganha/deployment	0.006s
```

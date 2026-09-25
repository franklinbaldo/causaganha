---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-95dnzq-check-go-tests-red"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal_id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
command: "cd deployment && go test ./... -v (rodado contra o deployment/djen_proxy.go original, antes de qualquer mudanca de producao)"
result: "failed"
evidence_id: "2026-09-25-exciting-mccarthy-95dnzq-evidence-red-go-tests"
summary: "Falha esperada (RED do TDD): 4 de 5 testes falham contra o codigo original, provando ao vivo que POST/PUT/DELETE/PATCH/OPTIONS eram aceitos e que /login, /swagger/*, /comunicacao eram encaminhados ao backend real. Ver evidence-red-go-tests para o output completo."
---

# Check: suite Go do djen_proxy (pre-fix, RED esperado)

```
$ cd deployment && go test ./... -v
--- FAIL: TestAllowed (0.00s)
--- FAIL: TestSecurityRejectsMutatingMethods (0.00s)
--- PASS: TestSecurityAllowsGetOnWhitelistedPath (0.00s)
--- FAIL: TestSecurityRejectsGetOnLoginSwaggerAndBareComunicacao (0.00s)
--- FAIL: TestSecurityRejectsMutatingMethodEvenOffWhitelist (0.00s)
FAIL
```

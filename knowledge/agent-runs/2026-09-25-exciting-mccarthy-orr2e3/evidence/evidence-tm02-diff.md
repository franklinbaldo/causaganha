---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-orr2e3-evidence-tm02-diff"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal_id: "2026-09-25-exciting-mccarthy-orr2e3-goal-tm02-stale-doc"
kind: "diff"
reference: "docs/SECURITY_THREAT_MODEL.md (linha TM-02)"
summary: "Substituída a afirmação 'CF relay... mas ainda não stripa Authorization/Cookie explicitamente... essa lacuna específica permanece de baixo risco real e não foi fechada nesta rodada' por uma que reflete o código atual (`STRIP_REQUEST_HEADERS`/`STRIP_RESPONSE_HEADERS` em `deployment/relay-cf/src/index.js`, fechado pela PR #1634/commit `7b2aba7`). Coluna 'Gate automatizado' atualizada de 'pendente apenas para o CF relay (dead infra)' para citar os dois testes específicos que já cobrem o comportamento (`deployment/relay-cf/test/index.test.js`), verificados verdes nesta rodada (18/18, ver check-relay-cf-vitest)."
---

# Evidência: diff de correção do TM-02

git diff (resumo):
```
- CF relay já é HTTPS + GET/HEAD/POST e faz stripping mais forte dos headers de infraestrutura, mas ainda não stripa `Authorization`/`Cookie` explicitamente — documentado como dead infra (...), então essa lacuna específica permanece de baixo risco real e não foi fechada nesta rodada.
+ CF relay já é HTTPS + GET/HEAD/POST e agora também stripa `Authorization`/`Cookie` explicitamente das requests encaminhadas e `Set-Cookie` das respostas (`deployment/relay-cf/src/index.js::STRIP_REQUEST_HEADERS`/`STRIP_RESPONSE_HEADERS`, fechado pela PR #1634/commit `7b2aba7`) — documentado como dead infra (...), mas o stripping de headers sensíveis em si está feito, não pendente.

- ...; pendente apenas para o CF relay (dead infra).
+ ...e para o CF relay (`deployment/relay-cf/test/index.test.js::"strips Authorization and Cookie before forwarding upstream"`/`"strips Set-Cookie from the upstream response"`, 18/18 verde).
```

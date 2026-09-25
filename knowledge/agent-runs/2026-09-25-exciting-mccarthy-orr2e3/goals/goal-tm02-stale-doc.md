---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-orr2e3-goal-tm02-stale-doc"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal: "Corrigir a linha TM-02 de `docs/SECURITY_THREAT_MODEL.md`, que afirma que o CF relay (`deployment/relay-cf/src/index.js`) ainda não faz stripping de `Authorization`/`Cookie`, quando o código e os testes atuais (desde a PR #1634, commit `7b2aba7`) já fazem exatamente isso."
rationale: "`docs/SECURITY_THREAT_MODEL.md` é documentação viva consultada por toda rodada futura para decidir o que ainda precisa de trabalho de segurança (inclusive por esta mesma rodada, na leitura inicial). A linha TM-02 diz hoje 'CF relay... ainda não stripa Authorization/Cookie explicitamente... pendente apenas para o CF relay (dead infra)' -- mas `deployment/relay-cf/src/index.js` já inclui `authorization`/`cookie` em `STRIP_REQUEST_HEADERS` e `set-cookie` em `STRIP_RESPONSE_HEADERS`, com dois testes dedicados (`deployment/relay-cf/test/index.test.js`: 'strips Authorization and Cookie before forwarding upstream', 'strips Set-Cookie from the upstream response') e o próprio `deployment/relay-cf/README.md` já documenta corretamente esse comportamento. Deixar a linha do threat model desatualizada nessa direção específica (marcando como pendente algo que já está feito) é o tipo de drift que pode levar uma rodada futura a reabrir/reimplementar trabalho já concluído, ou a confiar erroneamente que outra parte do TM-02 (que de fato lista pendências reais, como as quotas de deploy do TM-06) está no mesmo nível de incerteza."
success_signal: "A linha TM-02 de `docs/SECURITY_THREAT_MODEL.md` (colunas 'Estado atual' e 'Gate automatizado') não afirma mais que o CF relay não faz stripping de Authorization/Cookie/Set-Cookie; cita a PR/commit que fechou o gap e os testes que o cobrem; nenhuma outra reivindicação da linha (djen_proxy.go, Python relay) é alterada sem verificação equivalente."
status: "achieved"
---

# Goal: corrigir TM-02 desatualizado (CF relay já stripa Authorization/Cookie)

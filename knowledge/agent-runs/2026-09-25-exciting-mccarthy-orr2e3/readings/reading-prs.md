---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-orr2e3-reading-prs"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
subject: "open_prs"
reference: "GitHub pull requests abertas, franklinbaldo/causaganha (list_pull_requests, state=open, 5 abertas) + PRs fechadas/mescladas investigadas: #1629, #1630, #1634"
finding: "5 PRs abertas: #1653 (docs, closeout do relatório AgentRun de r0zxiq, branch alheia `claude/exciting-mccarthy-r0zxiq`) -- CI 14/14 verde, mas a tentativa de merge por esta sessão falhou com erro 405 do GitHub ('Required status check \"GitGuardian Security Checks\" is expected', apesar do check run correspondente aparecer como completed/success na lista) -- não repetida uma segunda vez além do primeiro retry (mesmo erro), deixada para uma rodada futura ou o dono humano, sem tocar a branch alheia. #1643/#1644/#1645 (branches `codex/2026-09-25/...`, ferramenta externa) seguem sem investigação profunda, mesma decisão de rodadas anteriores. #1353 (dependabot) baixa prioridade. Investigação por trás da issue #950: PR #1629 ('security(mcp): add per-client rate limit... (#950)', mesclada 09:27:12Z) fecha explicitamente só o TM-06 do threat model (rate limit por cliente na camada de aplicação), com o próprio corpo documentando 'Pendente: quotas/abuse controls na própria camada de deploy (Cloud Run) -- fora do que uma sessão sem acesso a infraestrutura de deploy pode fechar'; como o título/corpo referenciava '#950' com linguagem de closing keyword, o merge fechou a issue inteira via automação do GitHub, não por decisão humana explícita de que o rollout remoto estava pronto. PR #1630 (mesclada 10:15:17Z, ~48min depois) registra esse merge de #1629 como 'ação de continuidade' no início de seu próprio texto, sem perceber/mencionar que isso havia fechado #950 de forma incompleta. Investigação também confirmou, via `git log -p`, que a PR #1634 ('security(relay): close Set-Cookie gap + CF relay egress policy', mesclada 08:44:55Z -- ANTES de #1629/#1630) já havia adicionado o stripping de `Authorization`/`Cookie`/`Set-Cookie` ao `deployment/relay-cf/src/index.js`, com testes (`deployment/relay-cf/test/index.test.js`) e atualização do `README.md` do relay-cf -- mas a atualização de `docs/SECURITY_THREAT_MODEL.md` TM-02 feita depois (por #1630, que editou TM-03 na mesma rodada, ou por uma rodada anterior a #1634) nunca foi corrigida para refletir esse merge: a linha TM-02 ainda hoje (no início desta rodada) afirma 'CF relay... ainda não stripa Authorization/Cookie explicitamente... pendente apenas para o CF relay (dead infra)', o que o código e os testes atuais contradizem diretamente. Nenhuma PR aberta toca `docs/SECURITY_THREAT_MODEL.md` nem `knowledge/backlog/issue-950.md`/`issue-951.md` -- sem risco de conflito para o trabalho desta rodada."
---

# Leitura: PRs em andamento

5 PRs abertas revisadas via `list_pull_requests`; nenhuma toca os
arquivos desta rodada. A leitura mais importante veio de PRs já
FECHADAS: `#1629`/`#1630` (fechamento indevido de `#950` via closing
keyword de um sub-item parcial) e `#1634` (fix real do CF relay cuja
correção nunca chegou ao texto do threat model). Ambos os achados
motivam o trabalho desta rodada.

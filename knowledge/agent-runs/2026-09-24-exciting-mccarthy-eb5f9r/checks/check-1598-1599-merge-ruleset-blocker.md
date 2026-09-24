---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-eb5f9r-check-1598-1599-merge-ruleset-blocker"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
goal_id: "2026-09-24-exciting-mccarthy-eb5f9r-goal-unstick-continuity-prs"
command: "mcp__github__merge_pull_request para #1598 e #1599 (squash, expectedHeadSha do head de 2026-09-20)"
result: "fail-then-diagnosed"
evidence_id: "2026-09-24-exciting-mccarthy-eb5f9r-evidence-pr-1597-merged"
summary: "Ambas falharam com 405 'Repository rule violations found: Required status check \"GitGuardian Security Checks\" is expected. []', apesar de get_check_runs mostrar esse check como completed/success. #1597 (mesclada com sucesso no mesmo momento) tinha seu GitGuardian check refrescado no mesmo dia (2026-09-24); #1598/#1599 tinham o check de 2026-09-20, 4 dias parado. Diagnostico: o ruleset provavelmente nao reconhece um check-run 'stale' relativo a alguma mudanca de config/app entre 2026-09-20 e agora. Correcao aplicada: mcp__github__update_pull_request_branch para ambas (merge de main dentro da branch da PR via API do GitHub, sem usar git push local -- git push local para essas branches de outra sessao retornou 403, credencial desta sessao e escopada a claude/exciting-mccarthy-eb5f9r), o que dispara CI fresco incluindo um novo GitGuardian check-run. Ambas em mergeable_state=unstable (CI rodando) apos a atualizacao; merge sera retentado assim que os checks novos completarem."
---

# Check: bloqueio de merge por required-status-check obsoleto

`mcp__github__merge_pull_request` para #1598 e #1599 retornou, para as
duas, o mesmo erro 405: `Repository rule violations found\n\nRequired
status check "GitGuardian Security Checks" is expected.\n\n []`. Isso
apesar de `mcp__github__pull_request_read` (`get_check_runs`) mostrar
`GitGuardian Security Checks` como `status=completed,
conclusion=success` nas duas PRs.

A mesma tentativa para #1597 (mesclada com sucesso) tinha seu
`GitGuardian Security Checks` rodado nesta mesma manha (2026-09-24,
apos uma sessao anterior ter atualizado a branch), enquanto #1598 e
#1599 tinham o check de 2026-09-20 -- 4 dias parado, exatamente o
periodo em que as tres PRs ficaram sem acao. Hipotese mais provavel:
o ruleset de branch protection do repositorio passou a exigir esse
check nominalmente, ou a instalacao do app GitGuardian mudou, em algum
momento apos 2026-09-20 -- checks antigos deixaram de satisfazer a
regra mesmo aparecendo como verdes. **Isso e provavelmente a causa raiz
real do backlog de 4 dias**, nao (so) o runtime Wisk retornando
`no-eligible-session` -- mesmo se o Wisk tivesse tentado mesclar essas
PRs no formato antigo, teria batido no mesmo 405.

Acao tomada: `mcp__github__update_pull_request_branch` para as duas
(atualiza a branch da PR com o `main` mais recente via API do GitHub,
sem exigir push git local -- a credencial git desta sessao e escopada
a `claude/exciting-mccarthy-eb5f9r` e um `git push` local para as
branches de outra sessao retornou 403). Isso dispara um novo ciclo de
CI, incluindo um `GitGuardian Security Checks` fresco, que deve
satisfazer o ruleset. Resultado a ser confirmado em check subsequente
apos o CI completar.

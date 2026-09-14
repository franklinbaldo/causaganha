---
type: AgentCheck
id: "2026-09-14-exciting-mccarthy-bueov4-check-merge-pr-1484-strict-status-checks"
run_id: "2026-09-14-exciting-mccarthy-bueov4"
command: "mcp__github__merge_pull_request(pullNumber=1484) logo após mesclar #1483; depois mcp__github__update_pull_request_branch(pullNumber=1484); depois polling de GET /repos/.../commits/{sha}/check-runs até todos completos; depois novo mcp__github__merge_pull_request(pullNumber=1484)"
result: "passed"
evidence_id: "2026-09-14-exciting-mccarthy-bueov4-evidence-pr-1484-merged"
summary: "Merge de #1484 falhou inicialmente com mensagem enganosa sobre GitGuardian; causa raiz era strict_required_status_checks_policy no ruleset de main exigindo o check de novo após o branch ficar 'behind'. Resolvido com update_pull_request_branch + espera por CI verde, depois merge com sucesso (c65fd50)."
---

# Check: merge de PR #1484 exige branch atualizado sob strict required-status-checks

Achado operacional útil para rodadas futuras: este repositório tem um ruleset em `main` (`GET /repos/franklinbaldo/causaganha/rules/branches/main`) com `required_status_checks` = `GitGuardian Security Checks` e `strict_required_status_checks_policy: true`. Isso significa que, assim que outra PR é mesclada em `main`, qualquer PR aberta que ficar 'behind' precisa ter esse check obrigatório re-executado contra o head atualizado antes de poder ser mesclada -- mesmo que o check já tivesse passado contra a base antiga. A primeira tentativa de merge de #1484 (logo após mesclar #1483) falhou com `405 Repository rule violations found -- Required status check "GitGuardian Security Checks" is expected`, uma mensagem enganosa (o check já existia e tinha passado no head antigo) que na verdade significa 'seu branch está desatualizado, o check precisa rodar de novo'. Resolvido com `mcp__github__update_pull_request_branch` (merge não destrutivo de `main`, não um rebase/force-push), seguido de espera pela suíte de CI completa no novo head. Recomendação para rodadas futuras: ao mesclar duas ou mais PRs em sequência nesta rodada, esperar a atualização de branch + CI da segunda PR em vez de tentar o merge direto logo após a primeira.

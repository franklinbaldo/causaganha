---
type: AgentGoal
id: "2026-09-26-exciting-mccarthy-uz8msx-goal-close-stale-codex-prs"
run_id: "2026-09-26-exciting-mccarthy-uz8msx"
goal: "Fechar as 3 PRs externas do bot codex (#1643, #1644, #1645) que atacavam as 3 fatias de #1652/TM-16, já que as 3 fatias foram fechadas por trabalho próprio desta série de rodadas (item 1 direto em main pela rodada 230b86, item 2 pela PR #1657, item 3 pela PR #1659) -- cada uma com comentário explicando qual PR já mesclada substitui aquele diagnóstico."
rationale: "As 3 PRs estão stale (bases anteriores ao fix real, alguns checks vermelhos) e sem nenhuma ação prevista por 3+ rodadas consecutivas (230b86, szlcz8, e agora esta leitura) -- ficam como ruído permanente na lista de PRs abertas, fazendo rodadas futuras perderem tempo relendo o mesmo diagnóstico descartado repetidamente. Fechá-las com uma nota clara de qual PR própria as substitui é uma limpeza de board de baixo risco (não são trabalho em andamento de ninguém, são diagnósticos automáticos de um bot sem acompanhamento humano) e reduz a carga cognitiva de leitura de PRs abertas para toda rodada futura."
success_signal: "pull_request_read(1643/1644/1645).state == 'closed' com um comentário em cada uma (via add_comment ou issue_write equivalente) citando a PR própria que já fechou aquele item de #1652, com o rodapé de atribuição exigido."
status: "achieved"
---

# Goal: fechar as 3 PRs codex stale, superadas por #1652 já fechada

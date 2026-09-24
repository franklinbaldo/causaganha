---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-khpkk2-decision-close-1600-forward-lesson"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
goal_id: "2026-09-24-exciting-mccarthy-khpkk2-goal-land-batch26-resolve-stale-1600"
question: "PR #1600 propunha mesclar #1597/#1598, mas #1602 ja fez exatamente isso por outro caminho, com um relatorio mais preciso (inclui a causa raiz do bloqueio de merge). Mesclar #1600 mesmo assim (por ser trabalho ja iniciado), fechar sem aproveitar nada, ou extrair seletivamente o que ainda tem valor?"
choice: "Fechar #1600 sem mesclar, com um comentario explicando a superacao por #1602 e referenciando esta rodada. Extrair e aplicar diretamente em main, fora da PR, o unico paragrafo de conteudo novo que ela carregava: o append a knowledge/backlog/issue-1050.md::blocking_reason registrando que uma correcao pushada nao fecha sozinha a thread de revisao do Codex."
rationale: "Confirmado via diff local (git show do branch remoto vs. HEAD de main) que a mudanca em issue-1050.md e puramente aditiva e isolada -- 3 linhas (o campo blocking_reason mais os metadados last_verified_*), sem nenhum outro arquivo de dominio divergente de main. Mesclar a PR inteira reintroduziria 13 arquivos de relatorio AgentRun (mjd1vm) duplicando uma narrativa que #1602 ja documenta com mais precisao -- o tipo de bookkeeping cerimonial que o proprio hourly-loop.md ja identifica como desperdicio, mesmo estando essa regra formalmente escopada ao loop Wisk. Fechar preservando so o conteudo de valor e mais correto do que as duas alternativas extremas (mesclar tudo, ou descartar a licao de processo junto)."
---

# Decisao: fechar #1600 como superada, preservando a licao de processo

Ver `evidence-issue-1050-lesson-forwarded` para a aplicacao concreta.
`#1600` nao e mais o vetor certo para levar `#1597`/`#1598` a `main`
(isso ja aconteceu via `#1602`); mante-la aberta ou merge-la sem
ajuste seria puro custo de manutencao. O unico conteudo dela ainda
ausente de `main` -- uma licao de processo real sobre revisao de
codigo -- e preservado por aplicacao direta, nao por merge da PR
inteira.

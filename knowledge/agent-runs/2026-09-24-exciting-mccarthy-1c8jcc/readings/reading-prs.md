---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-prs"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
subject: "open_prs"
reference: "franklinbaldo/causaganha pull requests (list_pull_requests, state=open); pull_request_read get/get_status/get_check_runs/get_reviews/get_comments em #1619, #1605"
finding: "No inicio da rodada havia 3 PRs abertas: #1619 ('security(datajud): validate tribunal against canonical allowlist (#1615)', branch claude/exciting-mccarthy-q1x0on, de sessao concorrente que terminou minutos antes desta rodada comecar), #1605 (batch27 de #1050, branch claude/exciting-mccarthy-034xwb, mesma PR ja diagnosticada por 2+ rodadas anteriores) e #1353 (dependabot, parada ha 15 dias). #1619 tinha mergeable_state=clean, 10/10 check-runs completed/success (CodeQL, 4x Analyze, web, lint, archive-cors-proxy, tests(tjro), GitGuardian), 0 reviews bloqueantes (so um comentario do bot Codex avisando limite de uso atingido) -- trabalho pronto de outra sessao, mesma classe de continuidade que rodadas anteriores desta janela ja mesclaram (#1607/#1617 pela rodada p973xb). Mesclada nesta rodada via squash (sha 111dad0), fechando #1615/TM-07. #1605 permanece com mergeable_state=dirty (conflito real em data/segmenter/annotations/), mesmo diagnostico ja registrado por 2+ rodadas anteriores (e3tk18, p973xb): resolver exigiria push na branch de outra sessao concorrente sem permissao explicita desta sessao. Reconfirmado sem fato novo, nao selecionada. #1353 (dependabot) segue parada e fora de escopo."
---

# Leitura: PRs abertas

Releu as PRs abertas via `list_pull_requests` e buscou status,
check-runs, reviews e comentarios via `pull_request_read`.

`#1619` estava pronta para merge (CI 10/10 verde, sem review
bloqueante, `mergeable_state=clean`) — trabalho concluido por uma
sessao concorrente que fechou `#1615`/TM-07 (validacao de `tribunal`
contra allowlist canonico em `datajud_status`/`datajud_facetas`/
`processo_estado`, com `src/datajud/tribunais.py` novo). Mesclada logo
no inicio desta rodada, antes de qualquer trabalho de dominio, seguindo
o mesmo padrao de "aterrissar trabalho pronto primeiro" das rodadas
anteriores desta janela.

`#1605` (batch27, branch alheia) permanece com conflito real de merge,
mesmo diagnostico reconfirmado por 2+ rodadas anteriores — fora do
alcance desta sessao sem permissao explicita de push naquela branch.

`#1353` (dependabot) segue parada e fora de escopo, sem mudanca.

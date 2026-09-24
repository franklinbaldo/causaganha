---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-eb5f9r-decision-agentrun-vs-wisk-this-round"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
goal_id: "2026-09-24-exciting-mccarthy-eb5f9r-goal-unstick-continuity-prs"
question: "O prompt armazenado desta sessao agendada instrui explicitamente o fluxo classico AgentRun/scaffold, mas .claude/hourly-loop.md (atualizado em 2026-09-20) diz que o loop horario do projeto agora e operado exclusivamente pelo Wisk e instrui a nao criar novos AgentRuns nesse loop. Como proceder nesta rodada sem violar nenhuma das duas instrucoes nem duplicar/quebrar o mecanismo Wisk?"
choice: "Seguir o fluxo AgentRun/OKF exatamente como o prompt agendado instrui (este relatorio), sem tentar depurar ou substituir o runtime Wisk. Tratar a restricao de .claude/hourly-loop.md como escopada especificamente ao 'loop horario' operado pelo Wisk (uma automacao distinta desta sessao agendada), nao como proibicao geral de qualquer AgentRun futuro -- o proprio arquivo diz que o formato legado e preservado 'para auditoria e compatibilidade'. Nao reescalar a tensao AgentRun-vs-Wisk em si (instrucao explicita de rodadas anteriores), mas registrar como fato novo, digno de notificacao ao dono humano, que o Wisk esta retornando 'no-eligible-session' com 3 PRs verdes havia 4 dias sem acao -- isso e sintoma observavel e acionavel, distinto da questao de governanca ja escalada."
rationale: "Bloquear esta rodada inteira por causa da ambiguidade de qual mecanismo 'deveria' rodar desperdicaria a janela agendada sem entregar nada, e nenhuma das duas fontes de instrucao autoriza essa opcao. O trabalho concreto identificado (mesclar #1598/#1599/#1597) e correto e valioso sob qualquer um dos dois mecanismos -- nao depende de resolver a tensao de governanca para ser executado."
---

# Decisao: qual mecanismo de loop seguir nesta rodada

Ver `finding` da leitura `reading-okf` para o achado completo. A
decisao pratica: proceder com o relatorio `AgentRun` classico (esta
rodada), fazer o trabalho de destravar as PRs paradas identificado no
goal desta rodada, e reportar ao dono humano -- fora do OKF, via
notificacao -- que o runtime Wisk parece estar preso em
`no-eligible-session` apesar de trabalho pronto disponivel, como fato
novo desde a ultima escalacao de 2026-09-14.

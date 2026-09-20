---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-6nbygb-decision-follow-scaffold-continue-1050"
run_id: "2026-09-20-exciting-mccarthy-6nbygb"
goal_id: null
question: "O prompt agendado continua instruindo criar um novo AgentRun (scaffold), enquanto .claude/hourly-loop.md continua declarando o mecanismo legado para o loop horario -- a mesma tensao ja escalada em 2026-09-14 (to0ars) e reconfirmada em pelo menos 5 rodadas desde entao, sem mudanca do dono humano. Dado que nada mudou materialmente, esta rodada deve reescalar de novo via notificacao, ou seguir o precedente ja estabelecido?"
choice: "Seguir o precedente estabelecido: cumprir o scaffold AgentRun como o prompt agendado desta sessao explicitamente instrui, sem reescalar de novo -- a tensao ja foi escalada uma vez e reconfirmada em prosa por rodadas subsequentes sem produzir mudanca; uma nova notificacao proativa sobre o mesmo fato sem novidade seria ruido, nao sinal, para o dono do repositorio."
rationale: "O criterio de notificacao proativa deste ambiente e reservado para o momento em que uma condicao NOVA aparece ou muda -- nao para reafirmar repetidamente um fato ja comunicado e ja sem resposta por 6 dias/5+ rodadas. A decisao original de to0ars ja pesou os dois lados (nao decidir unilateralmente desligar o proprio agendamento vs. nao ficar silenciosamente incompativel com a politica do repo) e concluiu que seguir o scaffold escalando uma vez era o caminho certo; nada nesta rodada muda esse calculo. O trabalho real desta rodada (revisao independente e merge de PRs #1590/#1591 ja verdes, seguido por um novo lote de #1050 se o tempo permitir) fica completamente desacoplado dessa questao de meta-mecanismo, entao nao ha custo de oportunidade em manter o precedente."
---

# Decisão: manter o precedente (scaffold AgentRun, sem reescalar)

A tensão AgentRun-vs-Wisk permanece sem reconciliação do dono humano,
mas já foi escalada uma vez (2026-09-14) e reconfirmada em prosa por
múltiplas rodadas desde então sem produzir mudança no prompt agendado
nem em `.claude/hourly-loop.md`. Repetir a notificação sem fato novo
seria ruído. Esta rodada segue o scaffold como instruído e mantém o
trabalho de domínio real (PRs #1590/#1591, lote 25 de #1050 se houver
tempo) desacoplado da questão.

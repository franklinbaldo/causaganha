---
type: AgentDecision
id: "2026-09-17-exciting-mccarthy-0hjgmk-decision-follow-scaffold-verified-live-state"
run_id: "2026-09-17-exciting-mccarthy-0hjgmk"
goal_id: "2026-09-17-exciting-mccarthy-0hjgmk-goal-djen-sample-batch17"
question: "O prompt agendado desta sessao instrui criar um novo AgentRun a partir do scaffold, mas .claude/hourly-loop.md (commitado no mesmo repositorio) diz o oposto -- que novos AgentRuns nao devem ser criados em favor do runtime Wisk. Esse conflito ja foi escalado uma vez (2026-09-14, to0ars) via notificacao proativa e reconfirmado sem mudanca por pelo menos 7 rodadas desde entao (incluindo a imediatamente anterior, epgxv2). Deve esta rodada seguir o scaffold como escrito, ou reescalar/mudar de mecanismo por conta propria?"
choice: "Seguir o scaffold como instruido pelo prompt agendado -- criar o AgentRun, fazer o ciclo leitura/goal/decisao/evidencia/check, e usa-lo para avancar o lote 17 de #1050 (avanco real, ja verificado ao vivo como nao-duplicado por nenhuma sessao concorrente: document_count=138/val-test-ceiling=21/21, identico ao ultimo valor registrado pelo lote 16). Nao reenviar a notificacao proativa sobre a tensao AgentRun-vs-Wisk em si -- nenhum fato novo surgiu desde a escalada de to0ars que justifique gastar a atencao do dono de novo."
rationale: "O precedente de pelo menos 6 rodadas anteriores (bueov4, ez5wkn, 6kxfkh, zrek2s, j2t668, epgxv2) ja tratou exatamente essa pergunta e chegou a mesma conclusao, com a mesma logica: uma rodada autonoma e nao supervisionada nao deve decidir sozinha desligar seu proprio mecanismo de agendamento com base na sua propria leitura de um documento do repo -- o prompt agendado e um artefato que o dono controla e pode simplesmente nao ter atualizado ainda. A escalada ja aconteceu uma vez com contexto completo (to0ars); repetir a mesma notificacao sem fato novo desperdicaria a atencao do dono, que e precisamente o que as instrucoes desta sessao pedem para evitar. Verificar o estado ao vivo do repositorio antes de escolher trabalho (document_count, PRs abertas, pool de candidatos) garante que o trabalho real desta rodada fica desacoplado da questao nao resolvida -- o lote 17 avanca #1050 independentemente de como o dono eventualmente reconciliar os dois mecanismos."
---

# Decisao: manter o scaffold nesta rodada, nao reescalar sem fato novo

O prompt agendado desta sessao continua pedindo a criacao de um novo
`AgentRun`; `.claude/hourly-loop.md` diz o oposto. Como pelo menos 6
rodadas anteriores ja escalaram/reconfirmaram exatamente essa tensao sem
producao de mudanca no agendamento, esta rodada cumpre o scaffold como
instruido, verifica o estado ao vivo do repositorio (document_count=138,
val/test ceiling=21/21, 2 PRs abertas sem colisao) antes de selecionar o
lote 17, e nao reenvia a mesma notificacao proativa por falta de fato
novo.

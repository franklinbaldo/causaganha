---
type: AgentDecision
id: "2026-09-17-exciting-mccarthy-epgxv2-decision-follow-scaffold-verified-live-state"
run_id: "2026-09-17-exciting-mccarthy-epgxv2"
question: "O prompt agendado continua instruindo o scaffold AgentRun (criar run.md a partir de .claude/agent-run-scaffold.md em knowledge/agent-runs/) apesar de knowledge/agent-runs/index.md e .claude/hourly-loop.md tratarem esse mecanismo como legado em favor do runtime Wisk ('nao crie novos AgentRuns'). Como agir sobre essa tensao, e qual trabalho de dominio selecionar dado que a linhagem #1050 alterna entre os dois mecanismos concorrentes?"
choice: "Seguir o scaffold AgentRun para esta rodada (criar este relatorio, ler as 4 fontes exigidas, definir goal tipado), consistente com 6 decisoes anteriores sobre a mesma tensao, sem reenviar notificacao proativa sobre a tensao em si. Selecionar o lote 16 da linhagem #1050 como trabalho de dominio, apos confirmar ao vivo (scripts/segmenter_governance_status.py) que nenhuma sessao concorrente avancou o corpus desde a ultima rodada registrada (j2t668)."
rationale: "O system-reminder desta sessao declara explicitamente que as instrucoes do prompt agendado (armazenado por uma sessao autorizada) tem precedencia sobre o comportamento padrao. A tensao AgentRun-vs-Wisk ja foi escalada uma vez (to0ars, 2026-09-14) com contexto completo, e o dono ainda nao reconciliou os dois mecanismos -- isso e uma decisao dele em aberto, nao evidencia de que o agendamento foi descontinuado silenciosamente. Reenviar a mesma notificacao sem fato novo desperdicaria a atencao do dono (o guia de notificacoes desta sessao pede silencio quando nao ha novidade). Sobre o trabalho de dominio: a linhagem #1050 continua sendo o item com mais contexto acumulado, caminho de execucao ja provado por 15 lotes reais, e nenhuma issue aberta sugere prioridade maior -- verificar o estado ao vivo do corpus (document_count=132, identico ao ultimo valor registrado) confirma que nao ha colisao com trabalho concorrente antes de selecionar candidatos."
---

# Decisao: seguir o scaffold AgentRun, continuar a linhagem #1050

Mesma decisao de fundo que zrek2s/j2t668 e as 4 rodadas anteriores a
essas (seguir o prompt agendado explicito sem reenviar a notificacao ja
feita sobre a tensao AgentRun-vs-Wisk). Nenhum fato novo desta rodada
reabre essa tensao para uma nova escalada. A mitigacao real (verificar
estado ao vivo do repositorio antes de escolher candidatos, para nao
duplicar trabalho concorrente) foi aplicada via `scripts/segmenter_governance_status.py`
e um scan proprio do pool `data/segmenter_samples/*.jsonl` antes de
selecionar os 6 candidatos do lote 16.

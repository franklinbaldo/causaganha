---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-i23hxr-decision-agentrun-vs-wisk-no-new-fact"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
question: "Rodadas anteriores (eb5f9r, khpkk2) ja descobriram e escalaram ao dono humano, fora do OKF, a tensao entre a issue #1256 (decisao formal de aposentar AgentRun em favor do Wisk) e o gatilho agendado que ainda dispara esta sessao com .claude/agent-run-scaffold.md. Esta rodada deve reescalar de novo, tentar 'consertar' o gatilho, ou seguir o prompt agendado como as rodadas anteriores fizeram?"
choice: "Seguir o prompt agendado (criar o AgentRun, fazer trabalho de dominio real) sem reescalar a tensao de novo. Reconfirmado ao vivo que o Wisk continua sem sessao elegivel nesta janela (uv run wisk start -> blocked/no-eligible-session; uv run wisk session next -> null), o mesmo estado que as rodadas anteriores ja registraram -- nao ha fato novo. CronList (ferramenta desta sessao) nao lista nenhum job, confirmando que o gatilho que dispara esta sessao e externo a esta sessao e nao pode ser inspecionado nem corrigido daqui."
rationale: "Reescalar a mesma informacao sem fato novo seria ruido, nao sinal -- o proprio guia de rotinas agendadas deste ambiente pede silencio quando nada mudou. O trabalho de dominio real (goal-repair-audit-blind-spot) e correto e valioso sob qualquer resolucao futura dessa tensao, entao nao ha motivo para bloquea-lo esperando uma resposta que ja foi pedida por outras rodadas. Se uma rodada futura encontrar um fato genuinamente novo (ex.: o dono desativando o gatilho, ou o Wisk deixando de retornar no-eligible-session), essa sim justifica nova comunicacao."
---

# Decisao: nao reescalar AgentRun-vs-Wisk sem fato novo

Mantem a pratica ja estabelecida por `eb5f9r`/`khpkk2`/`my6ovw`. O
unico dado potencialmente novo verificado nesta rodada (`CronList`
vazio) apenas confirma que esta sessao nao tem meios de inspecionar
ou corrigir o gatilho agendado -- nao muda a decisao ja tomada pelo
dono em `#1256`, nem justifica interromper o trabalho de dominio
desta rodada.

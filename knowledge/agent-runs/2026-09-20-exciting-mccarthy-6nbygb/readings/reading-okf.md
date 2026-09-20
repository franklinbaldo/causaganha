---
type: AgentReading
id: "2026-09-20-exciting-mccarthy-6nbygb-reading-okf"
run_id: "2026-09-20-exciting-mccarthy-6nbygb"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-19-exciting-mccarthy-gbf44b/run.md"
finding: "knowledge/backlog/issue-1050.md documenta agora 23+ lotes reais mergeados (ate batch23/PR #1586) mais um 24o lote (#1590) ainda em PR aberta. A tensao AgentRun-vs-Wisk (.claude/hourly-loop.md declara o mecanismo AgentRun legado para o loop horario) continua sem reconciliacao do dono humano desde a escalada de 2026-09-14 (to0ars) -- reconfirmada em pelo menos 5 rodadas subsequentes sem mudanca no prompt agendado nem no hourly-loop.md. Nesta rodada o prompt agendado continua instruindo explicitamente o scaffold AgentRun, entao sigo o precedente estabelecido: cumprir o scaffold como instruido, sem reescalar de novo (ja escalado, sem mudanca material desde entao nao justifica uma nova notificacao)."
---

# Leitura: conhecimento OKF relevante

`knowledge/backlog/issue-1050.md` permanece o registro operacional mais
denso da linhagem do segmentador: contagens de `document_count`/teto
val-test por lote, 17 classes de risco numeradas, e um `last_verified_run_id`
que deve estar apontando para o lote 23 (Wisk) ou 22 (AgentRun), a
confirmar contra o texto completo do arquivo antes de editar.

`.wisk/knowledge/experiences/runs/` (fora do bundle OKF, mas relevante
para entender continuidade) tem pelo menos uma `LoopRun` recente
(20260919T232524Z) que a propria PR #1591 descreve como orfa e ja
fechada nesta madrugada -- ou seja, a rodada Wisk mais recente ja
tratou sua propria bookkeeping antes desta rodada AgentRun comecar.

A decisao registrada em `to0ars` (2026-09-14) de cumprir o scaffold e
escalar via notificacao continua sendo o precedente vigente: nao
reescalo de novo nesta rodada porque nada mudou materialmente desde a
ultima reconfirmacao (gbf44b, 2026-09-19) -- apenas registro a
continuidade da tensao aqui, como as rodadas anteriores fizeram.

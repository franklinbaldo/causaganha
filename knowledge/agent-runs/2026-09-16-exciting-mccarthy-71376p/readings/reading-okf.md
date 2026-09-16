---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-71376p-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-71376p"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/backlog/issue-1050.md, knowledge/agent-runs/2026-09-16-exciting-mccarthy-{zrek2s,imy2ed,hv2ep2}/"
finding: "AgentRun-vs-Wisk tension confirmed still live and unresolved by the repo owner, consistent with >20 prior reconfirmations since the first escalation (to0ars, 2026-09-14): knowledge/agent-runs/index.md and .claude/hourly-loop.md declare the AgentRun scaffold legacy/deprecated in favor of the Wisk runtime, but this session's scheduled prompt still hard-codes the legacy scaffold without qualification. No new fact changes the urgency for the human owner; following precedent, this round does not re-send the notification. NEW: the tension has now produced a concrete, material cost beyond duplicated batches -- a real merge conflict between two concurrently-developed batches (#1557/hv2ep2 and #1559/imy2ed) of the SAME lineage, both under the AgentRun mechanism, both unaware of each other because they ran in parallel. This round's actual work is resolving that conflict, which is itself evidence that the coordination gap the tension has flagged for two days is now costing real reconciliation effort, not just redundant batches."
---

# Leitura: conhecimento OKF relevante

Confirmação ao vivo de que `knowledge/agent-runs/index.md` e
`.claude/hourly-loop.md` continuam, sem alteração, declarando o mecanismo
`AgentRun`/scaffold legado em favor do runtime Wisk (`.wisk/knowledge/`).
O prompt desta sessão agendada continua, sem ressalva, instruindo o
scaffold legado como primeira ação obrigatória. Mais de 20 rodadas
anteriores desde `to0ars` (2026-09-14) já enfrentaram exatamente esta
tensão e convergiram na mesma decisão operacional: seguir a instrução
explícita do prompt agendado (que tem precedência declarada pelo próprio
system-reminder desta sessão), sem reenviar a notificação proativa já
feita, salvo fato novo que mude a urgência para o dono decidir.

## O que é novo nesta leitura

Até agora a tensão vinha custando principalmente *rodadas duplicadas*
(a mesma issue #1050 avançada em paralelo por AgentRun e Wisk, ou por
duas sessões AgentRun simultâneas, sem sobreposição de arquivo). Esta
rodada encontra o primeiro caso em que a concorrência produziu um
*conflito de merge real*: `PR #1557` (lote 9, rodada `hv2ep2`) e
`PR #1559` (lote 10, rodada `imy2ed`) partiram do mesmo commit-base
(`02c81bb`) e avançaram a mesma prosa (`knowledge/backlog/issue-1050.md`)
e o mesmo arquivo de teste
(`tests/segmenter_dataset/test_segmenter_governance_status.py`) de forma
incompatível. O custo agora é reconciliação manual, não apenas
desperdício de uma rodada. Isso é um dado relevante para uma futura
decisão do dono sobre consolidar os mecanismos, mas não é, por si só,
fato novo o bastante para justificar uma notificação proativa adicional
sem que o padrão de custo mude de categoria de novo (ex.: um conflito em
código de produção ou dado, não apenas prosa/teste) — mantendo o mesmo
critério usado pela linhagem inteira de decisões anteriores.

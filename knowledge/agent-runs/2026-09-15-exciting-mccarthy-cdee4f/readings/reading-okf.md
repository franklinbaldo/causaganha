---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-cdee4f-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-cdee4f"
subject: "okf_knowledge"
reference: ".claude/hourly-loop.md; knowledge/agent-runs/2026-09-15-exciting-mccarthy-rt6d4o/run.md; knowledge/agent-runs/2026-09-15-exciting-mccarthy-yz281l/run.md; docs/planning/parquet-storage-optimization-plan.md"
finding: ".claude/hourly-loop.md continua declarando sem ressalva que o mecanismo AgentRun/scaffold legado (knowledge/agent-runs/) não deve receber novas rodadas -- o loop horário passou a ser operado exclusivamente pelo runtime Wisk (.wisk/). `.wisk/` só contém `knowledge/` (sem LoopRun ativo nesta janela). Essa tensão já foi escalada por notificação proativa em duas rodadas (bueov4, to0ars, 2026-09-14) e reavaliada sem repetir a notificação em três rodadas seguintes (50ns70, yz281l, rt6d4o, todas 2026-09-15) por falta de fato novo desde a primeira escalada. Nada mudou nesta rodada -- sigo o mesmo raciocínio, priorizando a instrução explícita do prompt agendado e trabalho de domínio genuíno em vez de ficar ociosa ou repetir uma notificação já entregue. Knowledge de domínio mais relevante: run.md de rt6d4o registra no next_move que, dos critérios de aceite restantes de #1469, falta (a) scripts/reconcile_processos.py explicitar ordem física/grupos na escrita do índice, e (b) a igualdade direta implementada em processoCnj.ts fica dormente até a publicação real do acervo reordenado (#1472, bloqueada por IA_ACCESS_KEY/IA_SECRET_KEY, ausentes também nesta rodada: `env | grep -i 'IA_\\|ARCHIVE'` vazio). O item (a) não depende de credenciais IA e é o próximo avanço natural desta rodada."
---

# Leitura de conhecimento OKF

Li os dois AgentRuns mais recentes (yz281l, rt6d4o, ambos concluídos hoje 2026-09-15) e reconfirmei a tensão AgentRun-vs-Wisk em `.claude/hourly-loop.md`. Ambas as fontes convergem no mesmo próximo passo de domínio, registrado explicitamente no `next_move` de rt6d4o: explicitar ordem física e ROW_GROUP_SIZE na escrita de `indice_processual.parquet` em `scripts/reconcile_processos.py`, o único item textual de #1469 sem PR em voo que não depende de credenciais IA. Confirmei `env | grep -i 'IA_\|ARCHIVE'` vazio -- #1472 segue bloqueado, inalterado desde 11/09.

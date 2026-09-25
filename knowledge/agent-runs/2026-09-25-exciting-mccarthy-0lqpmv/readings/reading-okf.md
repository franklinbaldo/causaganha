---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-0lqpmv-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-25-exciting-mccarthy-qn6gvy/run.md + .claude/hourly-loop.md + knowledge/agent-runs/index.md"
finding: "A rodada mais recente concluída hoje (qn6gvy, completed_at=10:39:53Z, result_state='merged') fechou a fatia djen de TM-04/#1610 e deixou o cluster #1608-#1616 quase todo endereçado, com #1614 (supply-chain) citada como remanescente mas não selecionada por nenhuma rodada até agora -- confirma a leitura de issues desta rodada de forma independente. `.claude/hourly-loop.md` documenta uma tensão já conhecida e não nova: o mecanismo AgentRun (este mesmo scaffold) é tratado como legado, substituído pelo runtime Wisk para o loop horário normal ('não crie novos AgentRuns no loop horário'); múltiplas rodadas hoje (r2xele, 9t0p2a e outras) já registraram essa mesma tensão como issue #1256, já escalada, sem fato novo desde a última escalação -- não reescalada aqui. O prompt desta sessão agendada específica instruiu explicitamente o uso do scaffold AgentRun (não do Wisk), então este relatório segue esse mecanismo como as rodadas concorrentes de hoje já fazem, mantendo o padrão estabelecido em vez de introduzir um terceiro comportamento. Nenhum AgentRun anterior trabalhou em #1614; nenhum type/schema OKF específico para build/supply-chain existe hoje (AgentEvidence.kind é texto livre, já suficiente para registrar evidência de lockfile/digest/non-root sem precisar de um type novo)."
---

# Leitura: OKF (rodada anterior mais recente + tensão AgentRun/Wisk já conhecida)

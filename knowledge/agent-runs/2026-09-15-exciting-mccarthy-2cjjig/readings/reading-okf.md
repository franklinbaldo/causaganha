---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2cjjig-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md; .claude/hourly-loop.md; knowledge/agent-runs/2026-09-15-exciting-mccarthy-2jz691/run.md (rodada mais recente, terminada 11:44:45Z); docs/rfc/0012-segmenter-dataset-confiavel-baseline.md"
finding: "knowledge/agent-runs/index.md e .claude/hourly-loop.md continuam declarando, sem ressalva, que o mecanismo AgentRun/scaffold é legado e que o loop horário do CausaGanha passou a ser operado exclusivamente pelo runtime Wisk (`uv run wisk start`) -- a mesma tensão que a linhagem de hoje (bueov4, to0ars, 50ns70, yz281l, rt6d4o, cdee4f, 6d5vnd, wvzu11, 5crg57, virf8r, 7drjlg, 2jz691) já identificou e escalou por notificação proativa nas primeiras ocorrências, decidindo desde então não repetir a notificação sem fato novo (ver decision-follow-scheduled-scaffold-again de yz281l, reconfirmada por 2jz691). O prompt agendado que dispara esta sessão continua instruindo o scaffold AgentRun sem ressalva -- nada mudou no schedule nem em .claude/hourly-loop.md desde a última verificação (2jz691, 11:27-11:44Z). A rodada mais recente (2jz691) escalou RFC 0012/#1051 de review_count 8->11 (meta ~60, §5.4), corrigindo também um gap real (EXCLUDED_CATEGORIES duplicado entre scripts) via TDD, e deixou como next_move explícito continuar o mesmo mecanismo sobre o pool de candidatos sem review (agora 50 documentos pendentes: 61 documentos totais - 11 revisados)."
---

# Leitura: conhecimento OKF (AgentRun-vs-Wisk + continuidade RFC 0012)

Mesma decisão de toda a linhagem de hoje: seguir a instrução explícita do
prompt agendado (criar este AgentRun), sem enviar nova notificação sobre o
conflito AgentRun-vs-Wisk -- nada mudou desde a última avaliação (2jz691,
poucas horas atrás). Verificado ao vivo que não há PR nem trabalho Wisk em
voo nesta janela (reading-prs), então não há risco de duplicar/conflitar
com Wisk ao escolher trabalho de domínio. `uv run python
scripts/segmenter_governance_status.py` confirma o estado herdado:
document_count=61, review_count=11, evaluation_eligible_count=11,
blocked_on_reviews=false -- RFC 0012 §5.4 pede >=30 documentos de
validação e >=30 de teste adjudicados (~60 ReviewRecords no total) antes
do primeiro release do segmentador v8. #1051/RFC 0012 continua sendo a
única frente de domínio real, desbloqueada e não esgotada nesta sandbox
(cluster Parquet/CNJ #1468-1472 segue bloqueado por credenciais IA
ausentes).

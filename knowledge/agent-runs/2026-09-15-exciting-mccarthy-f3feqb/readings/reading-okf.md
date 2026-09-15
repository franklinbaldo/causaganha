---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-f3feqb-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md; .claude/hourly-loop.md; knowledge/agent-runs/2026-09-15-exciting-mccarthy-yz281l/run.md (rodada mais recente, terminada 02:41:18Z); docs/rfc/0012-segmenter-dataset-confiavel-baseline.md"
finding: "knowledge/agent-runs/index.md e .claude/hourly-loop.md continuam declarando, sem ressalva, que o mecanismo AgentRun/scaffold é legado e que o loop horário passou a ser operado exclusivamente pelo runtime Wisk ('não crie novos AgentRun aqui'). O prompt agendado que dispara esta sessão continua instruindo explicitamente o scaffold AgentRun sem ressalva -- a mesma tensão já identificada e escalada em rodadas anteriores (bueov4, to0ars) e desde então reconfirmada sem repetir a notificação por falta de fato novo (12+ rodadas hoje). Nada mudou desde a última avaliação: nenhuma edição em .claude/hourly-loop.md, knowledge/agent-runs/index.md nem no próprio prompt agendado. A rodada mais recente (yz281l) fechou o item 1 do checklist de #1468 (ROW_GROUP_SIZE 122880 pinado com evidência real) e apontou #1469 como candidato de próxima rodada, mas a issue #1051 segue sendo a de maior momentum real (sequência ininterrupta de PRs #1505..#1515 escalando review_count 0->15 hoje)."
---

# Leitura: conhecimento OKF (AgentRun-vs-Wisk + continuidade)

Decisão desta rodada, seguindo a linhagem inteira do dia: honrar a
instrução explícita do prompt agendado (criar este AgentRun) sem enviar
nova notificação proativa sobre o conflito AgentRun-vs-Wisk -- nada mudou
desde a última avaliação. `uv run python
scripts/segmenter_governance_status.py` confirma o estado herdado:
document_count=61, annotation_count=90, review_count=15,
evaluation_eligible_count=15, blocked_on_reviews=false. Um inventário ao
vivo (scratchpad) sobre os 46 documentos ainda sem review confirmou: os 10
que já têm 2 anotações não formam nenhum par independente
(`annotations_are_independent` retorna False para todos -- famílias
repetidas ou `seeded_with != "none"`), então a única frente real continua
sendo produzir uma segunda anotação genuinamente independente para um dos
36 documentos com exatamente 1 anotação capaz de independência.

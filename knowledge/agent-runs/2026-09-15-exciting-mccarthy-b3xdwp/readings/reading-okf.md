---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-b3xdwp-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md; .claude/hourly-loop.md; knowledge/agent-runs/2026-09-15-exciting-mccarthy-2cjjig/run.md (rodada mais recente, terminada 12:42:24Z); docs/rfc/0012-segmenter-dataset-confiavel-baseline.md"
finding: "knowledge/agent-runs/index.md e .claude/hourly-loop.md continuam declarando, sem ressalva, que o mecanismo AgentRun/scaffold é legado e que o loop horário passou a ser operado exclusivamente pelo runtime Wisk -- a mesma tensão já identificada e escalada (bueov4, to0ars) e desde então reconfirmada sem repetir a notificação por falta de fato novo (11+ rodadas hoje, última reconfirmação em 2cjjig). O prompt agendado que dispara esta sessão continua instruindo o scaffold AgentRun sem ressalva. A rodada mais recente (2cjjig) escalou RFC 0012/#1051 de review_count 11->13 (meta ~60, §5.4) e deixou como next_move explícito continuar sobre o pool agora com 48 documentos pendentes: 38 com exatamente 1 anotação (precisam de segunda independente) e 10 com 2 anotações mas nenhum par independente -- confirmado ao vivo nesta rodada via annotations_are_independent sobre os 10 (nenhum forma par: mesmo padrão de rodadas anteriores)."
---

# Leitura: conhecimento OKF (AgentRun-vs-Wisk + continuidade RFC 0012)

Mesma decisão de toda a linhagem de hoje: seguir a instrução explícita do
prompt agendado (criar este AgentRun), sem enviar nova notificação sobre o
conflito AgentRun-vs-Wisk -- nada mudou desde a última avaliação (2cjjig,
há menos de uma hora). Verificado ao vivo que não há PR nem trabalho Wisk em
voo nesta janela (reading-prs). `uv run python
scripts/segmenter_governance_status.py` confirma o estado herdado:
document_count=61, annotation_count=88, review_count=13,
evaluation_eligible_count=13, blocked_on_reviews=false. Rodei um script de
inventário ao vivo (find_candidates.py, scratchpad) sobre os 48 documentos
pendentes: 38 têm exatamente 1 anotação e nenhum dos 10 com 2 anotações
forma par independente (`annotations_are_independent` retornou False para
todos) -- confirma que não há atalho de "só adjudicar" nesta rodada
também, e que #1051/RFC 0012 continua sendo a única frente de domínio real,
desbloqueada e não esgotada nesta sandbox.

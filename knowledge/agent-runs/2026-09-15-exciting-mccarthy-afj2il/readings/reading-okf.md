---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-afj2il-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-f3feqb/run.md (rodada de continuidade mais recente mesclada em main)"
finding: "knowledge/agent-runs/index.md e .claude/hourly-loop.md continuam declarando, sem ressalva, que o loop horário migrou para o runtime do Wisk e que novos AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck não devem ser criados aqui -- mesma tensão identificada e resolvida da mesma forma por pelo menos 7 rodadas anteriores (bueov4, to0ars, 50ns70, 5crg57, 6d5vnd, virf8r, wvzu11, yz281l e agora f3feqb). O prompt agendado que dispara esta sessão continua instruindo explicitamente o scaffold AgentRun legado, sem menção ao Wisk. f3feqb (última rodada mesclada, HEAD atual) deixou como next_move continuar escalando #1051/RFC 0012 sobre o pool pendente (44 documentos, 34 com exatamente 1 anotação capaz de independência) e reconfirmou o cluster Parquet/CNJ (#1468-1472) esgotado no que não depende de credenciais IA ausentes."
---

# Leitura: knowledge OKF

Reconfirmado ao vivo: `knowledge/agent-runs/index.md` e `.claude/hourly-loop.md`
seguem sem alteração desde a última vez que essa tensão foi avaliada
(f3feqb, poucas horas atrás) -- o texto migratório para Wisk continua lá,
mas o prompt agendado que iniciou esta sessão não mudou e continua pedindo
explicitamente o scaffold `AgentRun` legado. Ver `decision-follow-scheduled-scaffold-again`
para a decisão tomada.

O relatório mais recente já mesclado em `main` (`2026-09-15-exciting-mccarthy-f3feqb`)
confirma: cluster Parquet/CNJ (#1468-1472) esgotado no que não depende de
`IA_ACCESS_KEY`/`IA_SECRET_KEY` ausentes; `#1051` (validação independente do
segmentador, RFC 0012) é a única frente de domínio real, desbloqueada e não
esgotada, com um mecanismo já validado por 12+ rodadas hoje
(`scripts/annotate_second_independent.py` + `scripts/adjudicate_segmenter_review.py`
+ `SegmenterDatasetStore.write_review`).

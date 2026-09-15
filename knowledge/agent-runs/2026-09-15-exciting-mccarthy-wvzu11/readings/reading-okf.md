---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-wvzu11-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, .wisk/knowledge/experiences/index.md, docs/rfc/0012-segmenter-dataset-confiavel-baseline.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-yz281l/ (relatório mais recente)"
finding: "knowledge/agent-runs/index.md e .claude/hourly-loop.md declaram o mecanismo AgentRun legado desde a migração para o Wisk (.wisk/); novas rodadas deveriam usar exclusivamente `wisk start`. Mas .wisk/knowledge/experiences/ não tem registro novo desde 2026-09-14, e o prompt agendado desta sessão continua instruindo explicitamente o scaffold AgentRun sem ressalva. Rodadas anteriores (bueov4, to0ars, 50ns70, yz281l) já identificaram essa tensão repetidamente e decidiram, de forma consistente, seguir a instrução explícita do prompt agendado sem repetir notificação quando nada mudou. O run.md mais recente (yz281l, mesma manhã) fechou o item 1 do checklist de #1468 (Parquet nativo por CNJ) via PR #1493/#1495/#1497/#1499/#1501, deixando apenas #1472 (rollout real) bloqueado por falta de IA_ACCESS_KEY/IA_SECRET_KEY. RFC 0012 (segmenter dataset v8) define a governança do dataset do segmentador: papel 'train' exige apenas 1 anotação; papéis 'validation'/'test' exigem um ReviewRecord aceito (adjudicação com >=2 anotações independentes). A store atual (data/segmenter) tem 61 documentos e 74 anotações mas nenhum ReviewRecord -- confirmado ao vivo rodando `assign-splits` contra a store real, que produz train=61/val=0/test=0, divergindo do data/segmenter_splits/ commitado (train=14/val=3/test=3) que o workflow real de treino (.github/workflows/train-segmenter.yml) ainda consome."
---

# Leitura de conhecimento OKF e estado dos mecanismos de rodada

Li o histórico recente de AgentRun (yz281l, mesma manhã) e a decisão consistente de rodadas anteriores sobre a tensão AgentRun-vs-Wisk: seguir o prompt agendado, sem repetir notificação quando nada mudou objetivamente. Verifiquei ao vivo que essa condição continua igual (nenhum commit novo em `.claude/hourly-loop.md`, nenhuma atividade Wisk desde 09-14) -- portanto mantenho a mesma linha desta vez também, registrada em decision-follow-scheduled-scaffold-again.

Além disso, ao investigar o cluster ativo #1047 (roadmap do segmentador OPF), descobri lendo `docs/rfc/0012-segmenter-dataset-confiavel-baseline.md` e `src/segmenter_dataset/splits.py` que a governança de papéis (train/val/test) da RFC 0012 exige `ReviewRecord`s aceitos para val/test, e que a store real não tem nenhum -- um achado relevante para orientar o goal desta rodada (ver goal e evidence).

---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-hv2ep2-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/backlog/issue-1050.md, uv run wisk start (live)"
finding: "knowledge/agent-runs/index.md explicitly declares the legacy AgentRun mechanism deprecated ('Legacy histórico... Não crie novos AgentRun...') in favor of a Wisk runtime, and .claude/hourly-loop.md says the hourly loop is operated exclusively by Wisk. Live-checked `uv run wisk start`: still returns {\"state\": \"blocked\", \"blockers\": [\"no-eligible-session\"]} -- same result every prior round today has reported, not new information. This session's own stored task prompt (not shown verbatim here, per the run instructions) hard-codes the legacy AgentRun scaffold as mandatory regardless. Per precedent from every round today (83kr8s, c4y4rc, k5wsee and others), followed the stored prompt and created this AgentRun report anyway, recording the tension here rather than re-escalating it (no new fact changed since the last round's evaluation -- wisk is still blocked, no human comment addressing the conflict has appeared on #1050/#1051/index.md). Also read knowledge/backlog/issue-1050.md in full (8 prior batches, 6 documented risk classes, tribunal-diversity-exhaustion note) as the primary domain knowledge source for this round's candidate selection and risk mitigation."
---

# Leitura: conhecimento OKF

Confirmada ao vivo a tensão já sinalizada por 2+ rodadas anteriores sem
resposta: `knowledge/agent-runs/index.md` e `.claude/hourly-loop.md`
declaram o mecanismo AgentRun legado como depreciado em favor do runtime
Wisk, mas o prompt armazenado desta sessão agendada continua exigindo o
scaffold AgentRun. `uv run wisk start` ao vivo retornou
`{"state": "blocked", "blockers": ["no-eligible-session"]}` — mesmo
resultado de toda rodada de hoje, não é fato novo. Seguido o precedente
estabelecido: relatório AgentRun criado, tensão registrada aqui (ver
decision-follow-scheduled-scaffold-despite-deprecation), nenhuma nova
notificação proativa enviada por falta de fato novo. `knowledge/backlog/issue-1050.md`
foi lido na íntegra como fonte primária de conhecimento de domínio: 8
lotes anteriores documentados, 6 classes de risco/defeito mapeadas, nota
de esgotamento de mineração por diversidade de tribunal (só
STM/TJAC/TJAM/TJAP/TJPE/TJSP/TRF1 sem candidato usável).

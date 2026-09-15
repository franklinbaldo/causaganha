---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-afj2il-decision-follow-scheduled-scaffold-again"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
question: ".claude/hourly-loop.md e knowledge/agent-runs/index.md continuam declarando, sem ressalva, que o mecanismo AgentRun é legado e que novas rodadas devem usar exclusivamente o Wisk. Pelo menos 8 rodadas consecutivas já identificaram essa tensão e decidiram seguir o scaffold mesmo assim; a última avaliação (f3feqb) decidiu não notificar de novo. O prompt agendado que disparou esta sessão não mudou. Esta rodada deve criar mais um AgentRun, e deve enviar mais uma notificação proativa sobre o mesmo conflito?"
choice: "Seguir a instrução explícita do prompt agendado e criar este AgentRun (feito). Não enviar nova notificação proativa: nada mudou sobre o conflito em si desde a última avaliação (f3feqb, poucas horas atrás). Continuar o trabalho de domínio já em andamento (escala de #1051/RFC 0012), que é a única frente real, desbloqueada e sem competir com nenhum trabalho Wisk em voo."
rationale: "O ritual de notificação existe para trazer atenção humana a uma condição nova ou não resolvida que precise de decisão. Notificar mais uma vez sobre exatamente o mesmo fato, sem nenhuma mudança de estado desde a rodada anterior no mesmo dia, seria ruído. Confirmado ao vivo que não há PR nem trabalho Wisk em voo (única PR aberta é o dependabot #1353, stale) -- não há risco de conflito ao escolher trabalho de domínio. Continuar #1051 em vez de reabrir o debate mecanismo-vs-mecanismo entrega avanço real ao produto, que é o que a rodada pede."
---

# Decisão: manter o scaffold AgentRun, sem nova notificação, continuar #1051

Mesma linha de pelo menos 8 rodadas anteriores hoje e ontem: o prompt
agendado continua instruindo o scaffold `AgentRun` legado sem ressalva,
apesar de `.claude/hourly-loop.md` e `knowledge/agent-runs/index.md`
dizerem para não criar novos. Sigo a instrução explícita da sessão. Não
envio nova notificação proativa -- nada mudou sobre o conflito desde a
avaliação mais recente (f3feqb, mesma manhã), e repetir o mesmo sinal sem
informação nova seria ruído, não sinal. Trabalho desta rodada: continuar
escalando ReviewRecords reais de #1051/RFC 0012, diretamente a partir do
next_move de f3feqb.

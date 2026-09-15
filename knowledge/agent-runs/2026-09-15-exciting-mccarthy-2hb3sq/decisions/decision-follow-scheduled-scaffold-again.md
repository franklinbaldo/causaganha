---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-2hb3sq-decision-follow-scheduled-scaffold-again"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
question: ".claude/hourly-loop.md e knowledge/agent-runs/index.md continuam declarando, sem ressalva, que o mecanismo AgentRun é legado e que novas rodadas devem usar exclusivamente o Wisk. Pelo menos 5 rodadas consecutivas (to0ars, bueov4 em 14/09; 50ns70, yz281l, f0q3d4 em 15/09) já identificaram essa tensão, 2 delas notificando o usuário proativamente. Nada mudou no hourly-loop.md nem no schedule desde a última avaliação (f0q3d4, ~1h atrás). Esta rodada deve criar mais um AgentRun, e deve enviar uma quinta notificação sobre o mesmo conflito?"
choice: "Seguir a instrução explícita do prompt agendado e criar este AgentRun (feito). Não enviar nova notificação: nada mudou sobre o conflito em si desde a última vez que foi avaliado (f0q3d4). Escolher como trabalho desta rodada a continuação direta do next_move de f0q3d4 (#1051), que não compete com nenhum PR ou handoff Wisk em andamento (única PR aberta de terceiros é #1528, fechamento de relatório da sessão bc9ae6, e #1353 dependabot stale)."
rationale: "O ritual de notificação existe para trazer atenção humana a uma condição nova ou não resolvida que precise de decisão -- repetir a mesma notificação pela quinta vez sem nenhuma mudança de estado seria ruído, não sinal, e a própria diretriz deste ambiente pede silêncio quando não há nada de novo para agir. Confirmei ao vivo (list_pull_requests, git fetch origin main) que não há PR nem trabalho Wisk de domínio em voo nesta janela, então escolher trabalho de domínio real não arrisca duplicar nem conflitar com nada em progresso."
---

# Decisão: manter o scaffold AgentRun, sem nova notificação, continuar next_move de f0q3d4

Mesma linha de raciocínio de pelo menos 4 rodadas anteriores que já
enfrentaram esta tensão exata. Sigo a instrução explícita do prompt
agendado. Não enviei nova notificação proativa. Trabalho desta rodada:
continuação direta e concreta do `next_move` registrado por f0q3d4,
recuperando os 2 documentos que aquela rodada tinha deixado órfãos.

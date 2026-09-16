---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-c4y4rc-decision-follow-scheduled-scaffold-again"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
question: "knowledge/agent-runs/index.md e .claude/hourly-loop.md continuam declarando, sem ressalva, que o mecanismo AgentRun e legado e que o loop horario real usa exclusivamente Wisk. Pelo menos 6 rodadas consecutivas ja identificaram essa tensao, 2 delas notificando o usuario proativamente sem resposta/mudanca de estado. Nada mudou desde a ultima avaliacao (2hb3sq). Esta rodada deve criar mais um AgentRun, e deve enviar mais uma notificacao sobre o mesmo conflito?"
choice: "Seguir a instrucao explicita do prompt agendado e criar este AgentRun (feito). Nao enviar nova notificacao: reconfirmei ao vivo (uv run wisk start -> blocked/no-eligible-session) que nada mudou sobre o conflito em si desde a ultima vez que foi avaliado."
rationale: "Repetir a mesma notificacao sem nenhuma mudanca de estado seria ruido, nao sinal -- a propria diretriz deste ambiente pede silencio quando nao ha nada de novo para agir. Confirmei ao vivo que nao ha PR nem trabalho Wisk de dominio em voo nesta janela, entao escolher trabalho de dominio real (o diagnostico do teto de RFC 0012 Sec 5 item 4) nao arrisca duplicar nem conflitar com nada em progresso."
---

# Decisao: manter o scaffold AgentRun, sem nova notificacao

Mesma linha de raciocinio de 6+ rodadas anteriores que ja enfrentaram esta
tensao exata. Sigo a instrucao explicita do prompt agendado. Nao enviei
nova notificacao proativa: nada mudou no hourly-loop.md, no index.md, ou
no estado do Wisk (`blocked`/`no-eligible-session`, mesmo bloqueio de toda
rodada anterior).

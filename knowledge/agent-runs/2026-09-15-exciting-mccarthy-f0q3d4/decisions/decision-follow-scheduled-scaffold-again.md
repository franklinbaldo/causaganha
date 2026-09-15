---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-f0q3d4-decision-follow-scheduled-scaffold-again"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: null
question: "index.md/hourly-loop.md continuam proibindo novos AgentRuns em favor do Wisk, e o prompt agendado continua instruindo o scaffold legado sem ressalva. uv run wisk start retornou blocked/no-eligible-session nesta janela. Seguir o scaffold de novo, e reenviar a notificação proativa já feita (to0ars, 14/09) sobre essa tensão?"
choice: "Seguir o scaffold AgentRun legado, como instruído pelo prompt agendado. Não reenviar notificação: nenhum fato novo desde a última reconfirmação (yz281l, mesma manhã) muda o que o mantenedor precisaria decidir."
rationale: "wisk start confirma que não há nenhum LoopRun Wisk ativo nem candidato elegível nesta janela -- seguir o scaffold legado não compete com, nem duplica, trabalho Wisk em curso. Uma quinta notificação sobre exatamente o mesmo conflito, sem nenhuma mudança de estado (nem no schedule, nem em hourly-loop.md, nem evidência de resposta do mantenedor), seria ruído, não sinal -- a própria diretriz de notificação deste ambiente pede silêncio quando não há nada de novo para agir."
---

# Decisão: manter o scaffold AgentRun, sem nova notificação

Mesma linha de toda a linhagem desde `bueov4` (14/09): o prompt agendado
desta sessão instrui literalmente o scaffold `AgentRun`, apesar de
`knowledge/agent-runs/index.md`/`.claude/hourly-loop.md` apontarem o
runtime Wisk como o mecanismo atual. Verifiquei ao vivo (`uv run wisk
start`) que não há nenhum trabalho Wisk em voo nesta janela — logo não há
risco de conflito ao escolher trabalho de domínio nesta rodada. A tensão de
mecanismo já foi escalada uma vez (to0ars, 14/09); sem fato novo desde a
última reconfirmação (yz281l, mesma manhã), repetir a notificação seria
ruído. Prossigo com trabalho de domínio genuíno nesta rodada.

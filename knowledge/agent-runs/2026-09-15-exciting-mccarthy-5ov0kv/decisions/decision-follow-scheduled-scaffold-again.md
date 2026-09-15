---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-5ov0kv-decision-follow-scheduled-scaffold-again"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: null
question: "Seguir o prompt agendado desta sessao (scaffold AgentRun legado) ou reenviar a notificacao proativa ja feita por to0ars em 14/09 sobre a tensao com knowledge/agent-runs/index.md e .claude/hourly-loop.md (Wisk)?"
choice: "Seguir o scaffold AgentRun legado, como instruido pelo prompt agendado, e nao reenviar a notificacao."
rationale: "Nenhum fato novo desde a ultima reconfirmacao (6kxfkh, mesma tarde) muda o que o dono do repositorio precisaria decidir: o prompt agendado continua, sem ressalva, instruindo o scaffold AgentRun; o index.md/hourly-loop.md continuam proibindo novos AgentRuns em favor do Wisk. Reenviar a mesma notificacao sem novidade seria ruido, nao sinal. O unico fato operacional novo desta rodada (duas sessoes rodando concorrentemente sobre o mesmo repositorio, nao apenas em sequencia) nao altera essa decisao -- e um achado tecnico sobre o proprio mecanismo, registrado em reading-okf.md para uma rodada futura avaliar, nao uma razao para escalar de novo agora."
---

# Decisão: continuar seguindo o scaffold AgentRun como instruído

Mesma decisão operacional de toda a linhagem desde `bueov4` (14/09):
seguir literalmente o prompt agendado desta sessão, que instrui o scaffold
`AgentRun` legado sem ressalva, em vez de migrar unilateralmente para o
runtime Wisk que `knowledge/agent-runs/index.md`/`.claude/hourly-loop.md`
apontam como o mecanismo atual. A tensão já foi escalada uma vez
(`to0ars`, 14/09) via notificação proativa ao dono do repositório; nenhuma
rodada desde então -- incluindo esta -- encontrou evidência de que o
schedule foi atualizado ou de que o dono respondeu, e nenhum fato novo
desde a última reconfirmação justifica repetir a notificação sem
novidade.

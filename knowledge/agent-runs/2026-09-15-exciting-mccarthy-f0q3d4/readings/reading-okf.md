---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-f0q3d4-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
source: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-yz281l/run.md (rodada anterior mais recente)"
finding: "index.md e hourly-loop.md continuam, sem ressalva, declarando o mecanismo AgentRun como legado em favor do runtime Wisk; `uv run wisk start` nesta janela retornou state=blocked/no-eligible-session (nenhum LoopRun ativo, nenhum candidato elegível). O prompt agendado desta sessão continua instruindo literalmente o scaffold AgentRun. A tensão já foi escalada uma vez via notificação proativa (to0ars, 14/09); nenhuma rodada desde então encontrou evidência de resposta do mantenedor ou de atualização do schedule."
---

# Leitura: knowledge OKF (agent-runs/index.md, hourly-loop.md, rodada anterior)

`knowledge/agent-runs/index.md` é explícito: "Não crie novos `AgentRun`,
`AgentReading`, `AgentGoal`, `AgentDecision`, `AgentEvidence` ou `AgentCheck`
aqui. Consulte `.claude/hourly-loop.md` para o entrypoint atual." E
`.claude/hourly-loop.md` aponta para `uv run wisk start` como golden path
exclusivo do loop horário, com `knowledge/agent-runs/` e
`.claude/agent-run-scaffold.md` explicitamente marcados como "legado
histórico".

Testei `uv run wisk start` ao vivo nesta janela: retornou
`{"state": "blocked", "blockers": ["no-eligible-session"], "candidates":
[], "run": null}` — nenhum LoopRun compatível vivo, nenhum trabalho Wisk
elegível para retomar agora. Confirma o mesmo padrão de toda rodada recente
desta linhagem (bueov4, to0ars, 50ns70, yz281l): o prompt agendado que
disparou esta sessão continua, sem ressalva, instruindo o scaffold AgentRun
legado; a tensão com o Wisk já foi escalada uma vez (to0ars, 14/09) via
notificação proativa; nenhuma rodada desde então -- incluindo a leitura do
`run.md` da rodada imediatamente anterior (yz281l, mesma manhã) -- encontrou
sinal de que o mantenedor respondeu ou de que o schedule foi atualizado.
Decisão de como proceder registrada separadamente em
`decisions/decision-follow-scheduled-scaffold-again.md`.

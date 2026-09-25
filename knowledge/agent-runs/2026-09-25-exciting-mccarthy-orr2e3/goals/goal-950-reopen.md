---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-orr2e3-goal-950-reopen"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal: "Corrigir o fechamento indevido da issue #950 (rollout MCP remoto): reabrir com um comentário factual distinguindo o que foi de fato concluído (TM-06, rate limiting) do que continua sem cumprir o critério de aceite do próprio corpo da issue (URL pública estável + prova de smoke real), e reconciliar `knowledge/backlog/issue-950.md`/`issue-951.md` com esse estado verificado."
rationale: "PR #1629 fechou #950 via closing keyword ('closes #950/TM-06') ao concluir apenas o sub-item de rate-limiting do threat model; o corpo da própria issue #950 lista 8 critérios de conclusão, dos quais nenhum sobre URL pública/smoke/`mcp-rollout-proof.json`/atualização de README-site foi cumprido. `mcp__github__actions_list` confirma `deploy-mcp.yml` com `total_count: 0` execuções -- o rollout nunca aconteceu. Como #951 (entrada pública `/agentes`) e #1093 (busca de teor) dependem explicitamente de #950 estar de fato pronta, deixar a issue fechada sem correção arrisca que uma rodada futura (ou o próprio dono humano, confiando no rastreador) acredite que o MCP remoto já está disponível e comece a construir/anunciar sobre uma premissa falsa -- exatamente o tipo de drift entre código/infraestrutura real e conhecimento registrado que este projeto trata como falha de correção (CLAUDE.md, seção Correctness)."
success_signal: "Issue #950 reaberta no GitHub com `state=open`, contendo um comentário novo que cita a evidência concreta (PR #1629/#1630, o `total_count: 0` de `deploy-mcp.yml`, e os critérios de aceite do corpo original ainda não cumpridos); `knowledge/backlog/issue-950.md` e `issue-951.md` atualizados com `last_verified_run_id`/`last_verified_at` desta rodada, mantendo `status: blocked` mas com a razão do bloqueio corrigida para reconhecer que a issue está sendo reaberta, não apenas 'ainda não trabalhada'."
status: "achieved"
---

# Goal: reabrir #950 (rollout MCP remoto fechado sem cumprir critério de aceite)

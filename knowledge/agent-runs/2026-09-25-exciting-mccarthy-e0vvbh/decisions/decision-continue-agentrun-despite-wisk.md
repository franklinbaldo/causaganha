---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-e0vvbh-decision-continue-agentrun-despite-wisk"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
goal_id: "2026-09-25-exciting-mccarthy-e0vvbh-goal-tribunal-coerente-manifesto"
question: "knowledge/agent-runs/index.md e .claude/hourly-loop.md dizem explicitamente para não criar novos AgentRuns (issue #1256, fechada, decidiu Wisk como runtime único do loop horário). O prompt desta sessão agendada, porém, instrui literalmente criar este relatório como primeira ação. Seguir o prompt da sessão ou a documentação do repositório?"
choice: "Seguir o prompt da sessão agendada e produzir este AgentRun, sem reescalar a tensão (issue #1256 já fechada, sem fato novo desde a última confirmação há poucas horas nesta mesma janela)."
rationale: "A tensão é conhecida e já foi identificada de forma consistente por quatro rodadas anteriores só hoje (3zkmxg, 95dnzq, r2xele, 9t0p2a). A decisão do dono humano em #1256 resolveu a arquitetura do *runtime do loop horário deste repositório* (usar Wisk), mas não altera a configuração da *tarefa agendada externa* que efetivamente invoca esta sessão -- essa configuração vive fora deste repositório e só o dono humano pode atualizá-la. Desviar unilateralmente do prompt explícito da sessão (por exemplo, tentando rodar `uv run wisk start` em vez do fluxo pedido) trocaria uma instrução operacional explícita e recente por uma inferência sobre o que o dono humano 'provavelmente quereria', sem um sinal novo que justifique a mudança de comportamento -- e o próprio scripts/check_agent_run_completeness.py continua rodando em CI sobre knowledge/agent-runs/, então o mecanismo legado continua sendo tolerado como válido pelo repositório mesmo pós-#1256. O avanço real desta rodada (TM-04 tribunal-coerente) não depende dessa escolha de bookkeeping; o registro aqui serve só para que uma rodada futura (ou o dono humano) não precise redescobrir a mesma tensão do zero."
---

# Decisão: manter o fluxo AgentRun desta sessão apesar da migração do repositório para Wisk

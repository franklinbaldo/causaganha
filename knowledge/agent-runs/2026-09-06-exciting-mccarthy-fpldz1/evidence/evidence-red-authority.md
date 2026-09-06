---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-fpldz1-evidence-red-authority"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
goal_id: "2026-09-06-exciting-mccarthy-fpldz1-goal-continue-with-agent"
kind: "test_red"
reference: "web/src/lib/agentContinuationQuestion.test.ts, run via `npm test -- --run src/lib/agentContinuationQuestion.test.ts` before web/src/lib/agentContinuationQuestion.ts existed"
summary: "Wrote 5 tests for buildAgentContinuationQuestion() (exact CNJ interpolation and determinism, a different CNJ producing different text, mentions of arquivo/estado/teor, mentions of ausência/indisponibilidade/proveniência/data, and never leaking an internal MCP tool name or a JSON brace) against a module that did not exist yet. vitest failed the whole suite file with 'Failed to resolve import \"./agentContinuationQuestion\"' — a natural RED, not a mutation-proof stand-in, since this is new code with no prior implementation to already satisfy the contract."
---

# Evidência RED — autoridade da pergunta ao agente

Suite falhou por import inexistente (`./agentContinuationQuestion`) antes da implementação — RED natural.

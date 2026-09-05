---
type: AgentGoal
id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal: "Make the AgentRun round-report completeness contract from PR #1141 actually enforceable, not just decorative SQL."
rationale: "The hourly-loop design (.claude/hourly-loop.md) depends on `okf-parser check` telling each round what its report still owes. Since okf-parser 0.45.6 ignores CHECK/NOT NULL constraints in both `check --relational-schema` and `compile_types`, that feedback loop is currently a no-op: an all-empty scaffold already validates as conformant, so no round would ever be told it is incomplete."
success_signal: "A project-owned completeness checker exists (scripts/check_agent_run_completeness.py), is covered by tests proving it flags every empty/invalid required AgentRun field and passes a fully filled one, and this very round's own run.md report becomes complete under it by the time the round closes."
status: "achieved"
---

# Goal: tornar o contrato de completude executável

Fechar o hiato entre o contrato SQL declarado e o que o okf-parser pinado realmente valida, com um checador próprio testado por TDD.

---
type: AgentGoal
id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal: "Extend the AgentRun completeness checker from PR #1144 to all six Agent* round-report types, and wire it into CI so an incomplete round report fails a pull request automatically instead of relying on the agent remembering to run the checker manually."
rationale: "PR #1144 closed the gap for AgentRun alone and explicitly recorded as next_move: extend the same completeness contract to AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck (only AgentRun was checked) and wire it into CI once there is more than one round's worth of reports. This round is exactly that second round — merging #1144 makes its own report the second real AgentRun-family instance in the bundle, so the CI gate now has something real to protect."
success_signal: "scripts/check_agent_run_completeness.py validates every markdown file under a knowledge/agent-runs/ tree (not just one run.md), dispatching per-type required-field/enum checks that mirror knowledge/okf.schema.sql for all six Agent* tables; a TDD RED test proves an incomplete sibling-type file (e.g. an AgentGoal missing success_signal) is now caught; GREEN after implementation; .github/workflows/okf.yml runs the checker over knowledge/agent-runs/ so a future round with an incomplete report fails CI."
status: "achieved"
---

# Goal: generalizar o checador de completude e ligá-lo ao CI

Fecha o `next_move` deixado por PR #1144: o contrato de completude passa a cobrir as seis tabelas `Agent*` e passa a ser verificado automaticamente, não apenas por convenção.

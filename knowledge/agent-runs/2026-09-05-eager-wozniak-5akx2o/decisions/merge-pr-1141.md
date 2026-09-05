---
type: AgentDecision
id: "2026-09-05-eager-wozniak-5akx2o-decision-merge-1141"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
question: "Merge the already-open PR #1141 (feat/okf-agent-run-contract) before starting this round's own work, or build a parallel AgentRun contract on this round's branch?"
choice: "Merge PR #1141 first (squash, commit 6c51749), then continue from the merged contract."
rationale: "All 10 CI checks were green, mergeable_state was clean, there were zero pending reviews, and a local `okf-parser check knowledge --relational-schema okf.schema.sql` run against the branch was conformant. Duplicating the same AgentRun/AgentReading/AgentGoal/... types on this branch instead would fork the contract into two divergent definitions headed for the same knowledge/okf.schema.sql file."
---

# Decisão: mesclar #1141 antes de avançar

Continuidade real, não reinvenção paralela do mesmo contrato.

---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-7gg7l1-check-okf-parser-final"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql (run after run.md, all readings/goals/decisions/evidence/checks for this round, and the 17 backlog timestamp refreshes)"
result: "passed"
evidence_id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-okf-conformant"
summary: "conformant=true, 0 diagnostics, 663 concepts (up from 641 baseline, reflecting this round's own OKF rows). All new AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck rows and the 17 refreshed BacklogItem rows resolve their foreign keys correctly."
---

# Check: okf-parser (final)

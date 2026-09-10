---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-yd5lu0-check-okf-parser-baseline"
run_id: "2026-09-10-exciting-mccarthy-yd5lu0"
goal_id: "2026-09-10-exciting-mccarthy-yd5lu0-goal-download-zip-cancels-siblings"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "failed"
evidence_id: "2026-09-10-exciting-mccarthy-yd5lu0-evidence-diff"
summary: "Run immediately after writing readings/goal/decision/evidence for this round but before creating run.md itself: OKF022 foreign-key errors on every new file (AgentReading/AgentGoal/AgentDecision/AgentEvidence, all referencing run_id='2026-09-10-exciting-mccarthy-yd5lu0') because no matching AgentRun row exists yet. Expected gap per the scaffold's own instructions -- resolved by writing run.md next, then re-running the check."
---

# Check: baseline do okf-parser antes do run.md

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` reporta 9 erros `OKF022` de chave estrangeira (`AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence` apontando para um `AgentRun` que ainda não existe) -- a lacuna esperada antes de escrever `run.md`.

---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-9xpeua-reading-okf"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
subject: "okf_knowledge"
reference: "knowledge/index.md, knowledge/okf.schema.sql, knowledge/agent-runs/2026-09-05-eager-wozniak-5akx2o/run.md, knowledge/agent-runs/2026-09-05-exciting-mccarthy-ejibsp/run.md"
finding: "Two prior AgentRun rounds exist, both about the OKF operational loop itself (building and then generalizing scripts/check_agent_run_completeness.py, wired into CI). The exciting-mccarthy-ejibsp report's next_move explicitly says: now that the AgentRun contract is enforced end to end, turn attention back to the open product backlog (#1128-#1139 web/UX, #1107 contract, #1047-1057 segmenter). knowledge/okf.schema.sql declares AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck with NOT NULL/CHECK constraints that scripts/check_agent_run_completeness.py enforces in CI on every PR touching knowledge/**. No AgentRun report yet documents product work outside the OKF loop itself — this round is the first to act on that next_move by picking a real product issue (#1135) instead of iterating on the report format."
---

# Leitura de conhecimento OKF

As duas rodadas anteriores investiram inteiramente em fazer o próprio `AgentRun` ser um contrato verificável (schema -> checker -> CI). O `next_move` da rodada mais recente pede explicitamente a virada para o backlog de produto. Esta leitura orienta a escolha do `AgentGoal` desta rodada: trabalho de produto real (#1135), não mais infraestrutura do loop.

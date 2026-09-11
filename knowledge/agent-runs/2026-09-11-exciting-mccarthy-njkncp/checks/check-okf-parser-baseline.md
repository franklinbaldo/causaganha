---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-njkncp-check-okf-parser-baseline"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Ran right after copying the scaffold to knowledge/agent-runs/2026-09-11-exciting-mccarthy-njkncp/run.md, before any AgentReading/AgentGoal existed. Output: {\"conformant\": true, \"diagnostics\": [], \"concept_count\": 1226, \"markdown_count\": 1229, \"reserved_count\": 3}. Structural check passes even with a draft run.md (empty required fields) -- the business-rule completeness gate lives in scripts/check_agent_run_completeness.py / tests/test_check_agent_run_completeness.py, not in okf-parser's own schema check, matching the scaffold's own documented behavior."
---

# Check: baseline okf-parser antes de preencher o relatório

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` → `conformant: true`, sem diagnósticos, mesmo com `run.md` ainda em rascunho.

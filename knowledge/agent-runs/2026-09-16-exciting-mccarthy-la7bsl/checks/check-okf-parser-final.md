---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-la7bsl-check-okf-parser-final"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
goal_id: "2026-09-16-exciting-mccarthy-la7bsl-goal-djen-sample-batch5"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, concept_count=1812, markdown_count=1815, reserved_count=3, diagnostics=[] -- run after all readings, the goal, both decisions, both evidence records, and completed_at/result_state/result_summary/next_move were filled in run.md."
---

# Check: okf-parser final

Bundle conformante com o `run.md` completo (leituras, goal, 2 decisoes,
2 evidencias, checks) e todos os campos finais preenchidos.

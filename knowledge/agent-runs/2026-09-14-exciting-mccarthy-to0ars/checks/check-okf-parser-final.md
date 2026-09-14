---
type: AgentCheck
id: "2026-09-14-exciting-mccarthy-to0ars-check-okf-parser-final"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-14-exciting-mccarthy-to0ars"
result: "passed"
evidence_id: null
summary: "Ran after filling in completed_at/result_state/result_summary/next_move and marking the goal achieved. okf-parser check: conformant=true, 0 diagnostics, concept_count=1315, markdown_count=1318, reserved_count=3. scripts/check_agent_run_completeness.py (the stricter required/non-empty/enum contract okf-parser's own PK/FK-only check does not enforce) reports all 12 documents in this round's directory, including run.md itself, as complete."
---

# Check: okf-parser + completude do relatório, após fechamento

`okf-parser check` -> `conformant: true`, 0 diagnósticos. `check_agent_run_completeness.py` -> todos os 12 documentos desta rodada, incluindo o próprio `run.md`, completos.

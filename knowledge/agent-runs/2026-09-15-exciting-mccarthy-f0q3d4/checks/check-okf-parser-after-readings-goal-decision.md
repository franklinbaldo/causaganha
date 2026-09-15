---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-f0q3d4-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: null
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: null
summary: "conformant=true, 0 diagnostics, concept_count=1691, markdown_count=1694 -- após criar run.md preenchido (id, readings, 2 goals, decision) e as 4 AgentReading + 2 AgentGoal + 1 AgentDecision desta rodada."
---

# Check: okf-parser após readings, goals e decision

Nenhum diagnóstico -- os foreign keys de `run_id`/`goal_id` resolvem
corretamente após `run.md` ganhar o `id` real.

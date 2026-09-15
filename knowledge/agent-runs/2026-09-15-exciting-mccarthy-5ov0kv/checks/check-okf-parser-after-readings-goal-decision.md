---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-5ov0kv-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: "2026-09-15-exciting-mccarthy-5ov0kv-goal-scale-segmenter-reviews"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: null
summary: "conformant=true, 0 diagnostics, concept_count=1672, markdown_count=1675 -- apos readings, goal e decisions desta rodada."
---

# Check: okf-parser apos readings, goal e decisions

Rodado apos criar `run.md` preenchido (id, readings, goal, decisions,
evidence do merge de #1527) e os quatro `AgentReading` + `AgentGoal` +
dois `AgentDecision`. Saida integral:

```json
{
  "concept_count": 1672,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 1675,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

Nenhum diagnostico -- os foreign keys de `run_id` resolvem corretamente
apos `run.md` ganhar o `id` real (antes disso, OKF022 apontava FK
pendente em cada `AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`
desta rodada).

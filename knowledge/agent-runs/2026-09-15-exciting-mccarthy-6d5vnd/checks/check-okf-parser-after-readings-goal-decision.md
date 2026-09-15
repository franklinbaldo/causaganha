---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-6d5vnd-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
goal_id: "2026-09-15-exciting-mccarthy-6d5vnd-goal-bloom-filter-a1c"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Após criar run.md, as 4 leituras iniciais, o goal e a primeira decisão desta rodada, o bundle knowledge/ segue conformant=true (1397 concepts, 0 diagnostics). Confirma que a estrutura do relatório está correta antes de começar o trabalho de domínio (benchmark + código)."
---

# Check: okf-parser após scaffold + 4 leituras + goal + decisão

Rodado logo após criar `run.md`, as 4 leituras obrigatórias (`AgentReading`), o `AgentGoal` (goal-bloom-filter-a1c) e a primeira `AgentDecision` (decision-follow-scheduled-scaffold-again). Resultado:

```json
{
  "concept_count": 1397,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 1400,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

`conformant: true`, sem diagnósticos -- confirma que a estrutura do relatório está correta antes de começar o trabalho de domínio (benchmark + código).

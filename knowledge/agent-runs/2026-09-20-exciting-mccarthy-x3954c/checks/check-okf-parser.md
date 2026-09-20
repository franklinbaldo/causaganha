---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-x3954c-check-okf-parser"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: null
summary: "0 diagnosticos apos escrever run.md, readings, goal, decisions e evidence deste relatorio (rodado imediatamente apos criar run.md, resolvendo os erros OKF022 de foreign key que apareciam quando so os arquivos filhos existiam sem o run.md pai)."
---

# Check: okf-parser check knowledge

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{ "diagnostics": [], "markdown_count": 2048+, "reserved_count": 3, "root": "..." }
```

0 diagnósticos. Antes de `run.md` existir, o mesmo comando reportava
9 erros `OKF022` (foreign key `run_id` sem `AgentRun` correspondente)
para cada `AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`
já escrito — resolvido assim que `run.md` foi criado com o `id`
correspondente.

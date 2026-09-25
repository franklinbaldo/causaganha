---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-95dnzq-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnosticos, apos run.md ser preenchido com todos os campos obrigatorios (completed_at, primary_goal_id, result_summary, next_move) e o goal marcado 'achieved'. 2192 concepts, 2195 markdown files."
---

# Check: okf-parser final

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2192,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2195,
  "reserved_count": 3
}
```

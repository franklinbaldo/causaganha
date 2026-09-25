---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-p973xb-check-okf-parser-final"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnosticos, apos run.md ser preenchido com todos os campos obrigatorios (completed_at, primary_goal_id, result_summary, next_move) e todos os IDs de reading/goal/decision/evidence/check referenciados existirem. 2144 concepts, 2147 markdown files."
---

# Check: okf-parser final

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2144,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2147,
  "reserved_count": 3
}
```

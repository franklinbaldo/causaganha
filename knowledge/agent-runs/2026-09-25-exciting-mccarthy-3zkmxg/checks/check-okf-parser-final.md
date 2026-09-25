---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-3zkmxg-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnosticos, apos run.md ser preenchido com todos os campos obrigatorios (completed_at, primary_goal_id, result_summary, next_move) e todos os IDs de reading/goal/decision/evidence/check desta rodada existirem e serem referenciados corretamente. 2174 concepts, 2177 markdown files."
---

# Check: okf-parser final

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2174,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2177,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

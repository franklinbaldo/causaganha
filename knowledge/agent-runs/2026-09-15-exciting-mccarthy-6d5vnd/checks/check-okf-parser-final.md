---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-6d5vnd-check-okf-parser-final"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
goal_id: "2026-09-15-exciting-mccarthy-6d5vnd-goal-bloom-filter-a1c"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Rodado após preencher completed_at/result_summary/next_move em run.md e registrar a segunda decisão (decision-covering-index-not-needed) e os checks intermediários. conformant=true, 1404 concepts, 0 diagnostics -- confirma que o relatório final da rodada está bem formado antes de commitar/abrir a PR."
---

# Check: okf-parser final

```json
{
  "concept_count": 1404,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 1407,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

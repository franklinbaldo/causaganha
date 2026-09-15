---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-6d5vnd-check-okf-parser-after-merge"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
goal_id: "2026-09-15-exciting-mccarthy-6d5vnd-goal-bloom-filter-a1c"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Rodado após PR #1501 mesclada (fa7318d) e as evidências evidence-pr-opened/evidence-pr-merged registradas. conformant=true, 1407 concepts, 0 diagnostics. Confirma que o relatório da rodada, incluindo a correção de CI (kind enum) e o fechamento, está bem formado antes de escrever o cabeçalho final de run.md."
---

# Check: okf-parser após merge

```json
{
  "concept_count": 1407,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 1410,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

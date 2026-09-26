---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-sg2540-check-okf-parser-baseline"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Bundle conformant before this round's writes: 0 diagnostics, 2580 concepts."
---

# Check: okf-parser baseline (before this round's writes)

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2580,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2583,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-5pnpmt-check-okf-parser-final"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnosticos, apos este run.md e todos os documentos AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck desta rodada serem preenchidos. 2177 concepts, 2180 markdown files."
---

# Check: okf-parser final

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2177,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2180,
  "reserved_count": 3
}
```

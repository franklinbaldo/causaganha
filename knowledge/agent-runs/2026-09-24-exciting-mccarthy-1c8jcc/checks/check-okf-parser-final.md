---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-1c8jcc-check-okf-parser-final"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnosticos, apos run.md ser preenchido com todos os campos obrigatorios (completed_at, primary_goal_id, result_summary, next_move), o goal ser marcado 'achieved', e o campo 'kind' de evidence-red-workflow-injection-demo ser corrigido de 'investigation_result' (invalido) para 'runtime' (valor aceito por scripts/check_agent_run_completeness.py). 2160 concepts, 2163 markdown files."
---

# Check: okf-parser final

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2160,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2163,
  "reserved_count": 3
}
```

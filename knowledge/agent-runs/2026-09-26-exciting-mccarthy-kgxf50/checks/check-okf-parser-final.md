---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-kgxf50-check-okf-parser-final"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-26-exciting-mccarthy-kgxf50"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-reviews-ingested"
summary: "okf-parser: conformant, 0 diagnostics, 2561 concepts (up from 2545 at session start). check_agent_run_completeness.py over this round's own report tree: all 16 files complete, 0 missing fields."
---

# Check: final okf-parser + completeness re-check

```
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{
  "concept_count": 2561,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2564,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}

$ uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-26-exciting-mccarthy-kgxf50
(all 16 files ✅ complete)
```

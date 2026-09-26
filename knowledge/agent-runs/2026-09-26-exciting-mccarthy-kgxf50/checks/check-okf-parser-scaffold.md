---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-kgxf50-check-okf-parser-scaffold"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pass"
evidence_id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-red-test"
summary: "Baseline check before this round's own writes: conformant, 0 diagnostics, 2545 concepts. HEAD at 8802e8c (merge of PR #1669, closing out round p08457). 0 open PRs -- clean slate, no in-flight work to resume."
---

# Check: okf-parser baseline before this round's writes

Ran at session start, before creating this run's own OKF files, to
confirm the bundle is conformant prior to any new writes this round.

```
{
  "concept_count": 2545,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2548,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

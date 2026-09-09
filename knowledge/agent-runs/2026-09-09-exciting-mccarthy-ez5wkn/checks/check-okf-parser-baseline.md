---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ez5wkn-check-okf-parser-baseline"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "{\"concept_count\": 971, \"conformant\": true, \"diagnostics\": [], \"markdown_count\": 974, \"reserved_count\": 3}. Run after scaffolding this round's run.md, its four initial readings, and the decision to keep using the legacy AgentRun scaffold despite the Wisk migration notice -- bundle conformant, no schema diagnostics, before goal selection. Also run right after merging PR #1362 (dangling from round qvqmci) and closing out qvqmci's report via PR #1363 -- both already reflected in this concept count."
---

# Check: okf-parser (baseline, início da rodada)

Bundle conformante no início da rodada, após as leituras iniciais e o fechamento da PR #1362/relatório qvqmci.

---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-buxwff-check-okf-parser-baseline"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
goal_id: "2026-09-06-exciting-mccarthy-buxwff-goal-agents-home-discovery"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Run at the very start of the round, before creating this round's own report tree: conformant=true, 0 diagnostics, concept_count=483. Confirms the knowledge bundle was structurally sound before this round's writes, so any diagnostic surfaced by a later run of the same command is attributable to this round's own report tree, not pre-existing drift."
---

# Check: baseline do okf-parser antes de escrever o relatório

`conformant: true`, `diagnostics: []`, `concept_count: 483` no início da rodada — linha de base limpa.

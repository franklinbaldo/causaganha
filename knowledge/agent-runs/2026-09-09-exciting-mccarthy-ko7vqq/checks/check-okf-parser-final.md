---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ko7vqq-check-okf-parser-final"
run_id: "2026-09-09-exciting-mccarthy-ko7vqq"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; and separately okf_parser.load_bundle(Path('knowledge')).is_conformant"
result: "passed"
summary: "Both signals agree after filling in this round's completion fields: CLI check {\"concept_count\": 1080, \"conformant\": true, \"diagnostics\": [], \"markdown_count\": 1083, \"reserved_count\": 3}; load_bundle(...).is_conformant == True, zero diagnostics. Run at the end of the round, before opening the PR."
---

# Check: okf-parser (final, antes de abrir a PR)

Ambos os sinais concordam: CLI e `load_bundle` conformantes, sem diagnósticos.

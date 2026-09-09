---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-v38h6d-check-okf-parser-baseline"
run_id: "2026-09-09-exciting-mccarthy-v38h6d"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql (run twice: once against the bare scaffold copy, once after writing the four AgentReading files)"
result: "passed"
summary: "Both runs returned conformant:true with 0 diagnostics (concept_count 1113 -> 1117 after the four readings were added). okf-parser's own PK/FK-metadata check does not enforce required-field emptiness (that gap is covered separately by scripts/check_agent_run_completeness.py, run later this round) -- this check only confirmed the bundle stayed structurally parseable at each step."
---

# Check: okf-parser baseline

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` conformante em dois pontos do inicio da rodada (scaffold vazio, depois com as quatro leituras).

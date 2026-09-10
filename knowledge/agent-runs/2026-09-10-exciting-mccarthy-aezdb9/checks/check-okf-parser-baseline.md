---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-aezdb9-check-okf-parser-baseline"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnostics, concept_count=1147 after the scaffold copy, the four required AgentReading instances, and run.md's id were in place. First cold run in this session's fresh sandbox needed UV_HTTP_TIMEOUT=180 to finish downloading the (large, network-dependent) dev dependency set within the retry window; once installed, the check itself completed in under a second."
---

# Check: okf-parser baseline após as quatro leituras

Bundle conformante e sem diagnósticos logo após as quatro `AgentReading` obrigatórias e o `id` do `run.md`.

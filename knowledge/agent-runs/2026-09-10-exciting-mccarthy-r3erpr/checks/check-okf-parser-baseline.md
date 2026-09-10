---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-r3erpr-check-okf-parser-baseline"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnostics, concept_count=1134 after the four required AgentReading instances (claude_md, issues, prs, okf) were written and run.md's id/reading-id fields were filled in. Confirms the four readings correctly resolve their run_id foreign key against the AgentRun row."
---

# Check: okf-parser baseline após as quatro leituras

Bundle conformante e sem diagnósticos após preencher `run.md` com `id` e os quatro `*_reading_id` e criar os quatro `AgentReading` correspondentes.

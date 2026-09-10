---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-yd5lu0-check-okf-parser-post-runmd"
run_id: "2026-09-10-exciting-mccarthy-yd5lu0"
goal_id: "2026-09-10-exciting-mccarthy-yd5lu0-goal-download-zip-cancels-siblings"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-10-exciting-mccarthy-yd5lu0-evidence-diff"
summary: "conformant=true, 0 diagnostics after writing run.md (fixing two field-value mismatches the earlier baseline check's absence had let slip through review: AgentReading.subject must be 'open_issues'/'open_prs'/'okf_knowledge', not 'issues'/'prs'/'okf'; AgentEvidence.kind must be 'test_red'/'test_green' with an underscore, not a hyphen -- confirmed against okf.schema.sql's CHECK constraints and aezdb9's own already-merged instances). Full repository pytest suite also passes in full with this run.md present, including the two generated-file completeness tests (Zod schemas, domain models) that fail on a draft AgentRun."
---

# Check: okf-parser após o run.md

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` -> `conformant: true`, 0 diagnósticos, após corrigir dois valores de enum (`subject`, `kind`) que não correspondiam ao `CHECK` do schema relacional.

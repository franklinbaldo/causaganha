---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-wvzu11-check-okf-parser"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-wvzu11-evidence-green-test"
summary: "conformant: true, diagnostics: [], concept_count: 1420."
---

# Check: okf-parser contra o bundle knowledge

Rodado após criar todas as leituras/goal/decisão/evidências e o run.md completo (com `completed_at` preenchido, já que esta rodada abre PR). Resultado: `"conformant": true`, `"diagnostics": []`, `concept_count: 1420`.

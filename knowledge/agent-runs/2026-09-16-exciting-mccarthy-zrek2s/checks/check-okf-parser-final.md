---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-zrek2s-check-okf-parser-final"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "observed"
evidence_id: null
summary: "conformant=true, concept_count=1831, markdown_count=1834, reserved_count=3, diagnostics=[]. Confirma o bundle conformante apos o run.md completo e a correcao dos campos de schema dos readings/goal/evidence/checks."
---

# Check: okf-parser final da rodada

Ultima verificacao do bundle `knowledge/` antes de rodar a suite
completa e abrir a PR. Conformante.

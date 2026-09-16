---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-96cgqx-check-okf-parser-after-evidence"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: null
summary: "conformant=true, concept_count=1940, markdown_count=1943, reserved_count=3, 0 diagnostics (apos corrigir evidence_id de \"\" para null em check-okf-parser-after-goal-decision.md, que violava a FK AgentCheck->AgentEvidence)"
---

# Check: okf-parser apos evidencias GREEN

Primeira execucao apos criar a evidencia GREEN encontrou um diagnostico
OKF022 (FK invalida) causado por um check anterior desta mesma rodada
usando `evidence_id: ""` em vez de `null` para "sem evidencia associada".
Corrigido e reexecutado -- conformante.

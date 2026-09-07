---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-kfv7sx-check-okf-parser-mid-round"
run_id: "2026-09-07-exciting-mccarthy-kfv7sx"
goal_id: "2026-09-07-exciting-mccarthy-kfv7sx-goal-mcp-public-profile"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "First run after adding decisions/evidence/checks caught OKF022: AgentCheck check-okf-parser-baseline.md had evidence_id set to an empty string, which the relational schema treats as a dangling foreign key (evidence_id references AgentEvidence(id) when present) rather than as 'no evidence' — the field must be omitted entirely, not set to \"\". Removed the empty field; re-ran: conformant=true, 0 diagnostics, concept_count=622, markdown_count=625. Used this round's own gap (an FK diagnostic) to fix a real authoring mistake mid-round, per the scaffold's own instructed loop."
---

# Check: okf-parser (meio da rodada)

Pegou `OKF022`: `evidence_id: ""` num `AgentCheck` é lido como FK pendente, não como ausência — campo opcional deve ser omitido, não vazio. Corrigido; nova rodada do check: `conformant: true`, 0 diagnostics.

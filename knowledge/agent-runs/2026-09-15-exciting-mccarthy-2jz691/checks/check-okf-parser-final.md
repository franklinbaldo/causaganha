---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-2jz691-check-okf-parser-final"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-2jz691-evidence-governance-status-after"
summary: "conformant=true, diagnostics=[], concept_count=1503, markdown_count=1506. Rodado após popular decisions/evidence/checks e corrigir dois desvios de schema encontrados nesta própria rodada (AgentCheck.evidence_id não pode ser string vazia -- precisa ser omitido ou apontar para um AgentEvidence real; AgentEvidence.kind usa os valores 'test_red'/'test_green', não 'test' genérico)."
---

# Check: okf-parser final desta rodada

`conformant: true`, `diagnostics: []`. Dois desvios de schema foram encontrados e corrigidos ao rodar o check pela segunda vez nesta rodada (ver summary) -- o próprio scaffold cumpriu seu papel de "usar as lacunas do relatório para orientar o trabalho", desta vez sobre o próprio formato dos registros OKF, não sobre o trabalho de domínio.

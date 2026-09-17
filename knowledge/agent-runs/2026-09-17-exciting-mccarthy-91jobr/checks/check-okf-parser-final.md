---
type: AgentCheck
id: "2026-09-17-exciting-mccarthy-91jobr-check-okf-parser-final"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-17-exciting-mccarthy-91jobr"
result: "passed"
evidence_id: null
summary: "conformant, 0 diagnostics (concept_count=1995, markdown_count=1998); todos os 9 documentos deste relatorio (run + 4 readings + 1 goal + 1 decision + 1 evidence + 2 checks) completos."
---

# Check: okf-parser e completude final do relatorio

Rodado apos preencher `completed_at`/`evidence_ids`/`result_summary`/
`next_move` do `run.md` e este proprio check. Conformante, 0
diagnosticos; `check_agent_run_completeness.py` confirma todos os
documentos do relatorio completos.

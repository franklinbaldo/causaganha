---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-szlcz8-check-okf-parser-scaffold"
run_id: "2026-09-25-exciting-mccarthy-szlcz8"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Rodado logo após criar o scaffold (run.md + 4 readings + 1 goal). conformant=true, diagnostics=[], concept_count=2451 (crescendo do valor da última rodada). Confirma a estrutura Markdown/YAML antes de iniciar o TDD; scripts/check_agent_run_completeness.py (via pytest) é quem exige completed_at/result_summary/next_move preenchidos, ainda vazios propositalmente neste ponto do rascunho."
---

# Check: okf-parser (durante o rascunho)

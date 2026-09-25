---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-qn6gvy-check-okf-parser-scaffold"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Rodado logo após criar o scaffold (run.md + 4 readings + 1 goal) e novamente após adicionar as decisions/evidences desta rodada. Ambas as vezes: conformant=true, diagnostics=[], concept_count crescente (2281 -> 2286). Confirma que a estrutura Markdown/YAML dos arquivos está correta; scripts/check_agent_run_completeness.py (rodado via pytest) é quem pega os campos obrigatórios do AgentRun ainda vazios (completed_at/etc.) enquanto o relatório está em rascunho -- comportamento documentado no próprio scaffold."
---

# Check: okf-parser (durante o rascunho)

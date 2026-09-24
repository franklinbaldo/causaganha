---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-e3tk18-check-agent-run-completeness-final"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
command: "uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/2026-09-24-exciting-mccarthy-e3tk18"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-green-fix-and-real-corpus-clean"
summary: "Todos os 12 documentos Agent* desta rodada (run.md, 4 readings, 1 goal, 1 decision, 2 evidences, 3 checks nesse ponto) reportados 'round report is complete'. Fecha a lacuna que okf-parser --relational-schema sozinho nao cobre (CHECK/NOT NULL nao aplicados pelo compile_types do okf-parser 0.45.6)."
---

# Check: gate de completude AgentRun

Reconfirma, com a ferramenta propria do projeto
(`scripts/check_agent_run_completeness.py`), que nenhum campo
obrigatorio de nenhum documento `Agent*` desta rodada ficou vazio --
gate que `okf-parser check --relational-schema` sozinho nao teria
pego.

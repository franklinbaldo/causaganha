---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-fipj1n-check-completeness-subject-enum-fix"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
command: "uv run pytest -q tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete"
result: "failed"
summary: "scripts/check_agent_run_completeness.py enforces subject in {claude_md, open_issues, open_prs, okf_knowledge, code, tests, ci, other} for AgentReading — este relatório inicialmente usou subject: 'issues'/'prs'/'okf' (valores fora do enum), tratados pelo checker como campo ausente. Corrigido para open_issues/open_prs/okf_knowledge nas 3 leituras afetadas (reading-issues.md, reading-prs.md, reading-okf.md); reading-claude-md.md já usava o valor correto por coincidência. Reexecução: 1 passed. Este achado é o próprio okf-parser/completeness check guiando a rodada em tempo real, como o protocolo do scaffold pede."
---

# Check: correção do enum `subject` em `AgentReading`

O gate de completude (`scripts/check_agent_run_completeness.py`, também
coberto por `tests/test_check_agent_run_completeness.py`) rejeitou 3 das
4 leituras desta rodada por usarem valores de `subject` fora do enum
esperado (`open_issues`/`open_prs`/`okf_knowledge`, não
`issues`/`prs`/`okf`). Corrigido; reexecução do teste específico e do
`okf-parser check` confirmam o bundle íntegro.

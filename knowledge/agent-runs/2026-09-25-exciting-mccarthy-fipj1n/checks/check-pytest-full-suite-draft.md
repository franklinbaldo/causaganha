---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-fipj1n-check-pytest-full-suite-draft"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
command: "uv run pytest -q"
result: "failed"
summary: "Rodado com run.md ainda em rascunho (completed_at/result_summary/next_move vazios). Exatamente 1 falha: tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete — o próprio gate autoreferencial que o scaffold documenta explicitamente ('Três testes falham enquanto o relatório está em rascunho'), não uma regressão do código tocado nesta rodada. Todos os outros testes, incluindo os módulos tocados (tjro_juris, causaganha.decisoes, causaganha_mcp), passaram."
---

# Check: pytest suite completa (rascunho)

Falha única e esperada em `test_check_agent_run_completeness.py`,
exatamente o autoreferencial que `.claude/agent-run-scaffold.md` já
documenta para um `run.md` ainda em rascunho — não uma regressão.
Confirma-se com o check final, após `run.md` ser preenchido.

---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-5txmmk-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
goal_id: "2026-09-25-exciting-mccarthy-5txmmk-goal-reconcile-identity-check"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnostics, apos o relatorio deste run.md ser finalizado (completed_at/result_summary/next_move preenchidos) e apos corrigir o valor de subject nas 3 leituras (reading-issues/reading-prs/reading-okf usavam 'issues'/'prs'/'okf'; o enum correto de AgentReading.subject e open_issues/open_prs/okf_knowledge -- descoberto por scripts/check_agent_run_completeness.py falhar em tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, corrigido, revalidado verde)."
---

# Check: okf-parser final

Validação final da árvore `knowledge/` (conformidade estrutural do
bundle OKF inteiro contra `okf.schema.sql`), depois de corrigir o
valor de `subject` em três `AgentReading` desta rodada (o checker de
completude de `AgentRun` usa um enum mais estrito do que a validação
estrutural genérica do `okf-parser` sozinha detecta).

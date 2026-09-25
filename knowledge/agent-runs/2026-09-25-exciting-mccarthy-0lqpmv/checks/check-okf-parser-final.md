---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-0lqpmv-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
goal_id: "2026-09-25-exciting-mccarthy-0lqpmv-goal-supply-chain-lock-nonroot"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run pytest -q tests/test_check_agent_run_completeness.py tests/web/test_generate_okf_zod_schemas.py tests/causaganha_mcp/test_okf_domain_models.py"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-0lqpmv-evidence-green-tests"
summary: "Após preencher completed_at/result_summary/next_move deste run.md: okf-parser conformant=true, diagnostics=[], concept_count=2305. Os três testes que o scaffold documenta como sensíveis a um AgentRun em rascunho (completude, paridade zod, paridade domain models) passam limpos com o relatório finalizado."
---

# Check: okf-parser + gates de completude (relatório finalizado)

---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-96cgqx-check-okf-parser-and-completeness-final"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs; uv run pytest tests/test_check_agent_run_completeness.py tests/web/test_generate_okf_zod_schemas.py::test_generated_zod_schemas_file_matches_current_knowledge_bundle tests/causaganha_mcp/test_okf_domain_models.py::test_generated_domain_models_file_matches_current_knowledge_bundle -q"
result: "passed"
evidence_id: "2026-09-16-exciting-mccarthy-96cgqx-evidence-batch13-green-ingested"
summary: "okf-parser: conformant=true, 0 diagnostics. check_agent_run_completeness.py: this round's run.md and all auxiliary files complete. The three tests that fail while an AgentRun is still a draft (test_main_over_this_rounds_own_report_tree_is_complete, test_generated_zod_schemas_file_matches_current_knowledge_bundle, test_generated_domain_models_file_matches_current_knowledge_bundle) all pass now that completed_at/result_summary/next_move are filled."
---

# Check final: okf-parser + completude do AgentRun

Ultimo check da rodada antes de abrir a PR. Confirma que o relatorio
`AgentRun` desta rodada esta completo e que os tres testes que dependem
disso (documentados pelo proprio scaffold como esperados falhar durante
o rascunho) voltaram a passar.

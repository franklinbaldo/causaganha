---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r0zxiq-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-green-datajud-read-side"
summary: "conformant=true, 0 diagnostics após preencher `run.md` com todos os IDs de reading/goal/decision/evidence/check. Reconfirmado em seguida que `tests/test_check_agent_run_completeness.py`, `tests/web/test_generate_okf_zod_schemas.py::test_generated_zod_schemas_file_matches_current_knowledge_bundle` e `tests/causaganha_mcp/test_okf_domain_models.py::test_generated_domain_models_file_matches_current_knowledge_bundle` voltam a passar juntos, sem precisar regenerar nenhum arquivo `.gen.ts`/`domain_models.py`."
---

# Check: okf-parser (final, após relatório preenchido)

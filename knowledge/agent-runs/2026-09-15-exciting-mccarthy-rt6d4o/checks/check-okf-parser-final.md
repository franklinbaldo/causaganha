---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-rt6d4o-check-okf-parser-final"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
goal_id: "2026-09-15-exciting-mccarthy-rt6d4o-goal-direct-equality-processo-cnj"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run pytest -q tests/test_check_agent_run_completeness.py tests/web/test_generate_okf_zod_schemas.py tests/causaganha_mcp/test_okf_domain_models.py"
result: "passed"
summary: "Após preencher completed_at/decision_ids/evidence_ids/check_ids/result_summary/next_move deste run.md: okf-parser -> conformant=true, diagnostics=[]. Os 3 testes da cascata prevista pelo rodapé do scaffold (completude do próprio relatório, schemas Zod derivados, domain models derivados) voltaram a passar sozinhos, sem regenerar web/src/lib/processoConsultar.gen.ts nem src/causaganha_mcp/_generated/domain_models.py -- confirma o comportamento já documentado pelo próprio scaffold."
---

# Check: okf-parser + cascata de completude, estado final antes do push

Confirma que o relatório desta rodada está estruturalmente completo e que a cascata de 3 falhas prevista no rodapé do scaffold se resolveu só com o preenchimento do `run.md`, sem tocar nos arquivos gerados.

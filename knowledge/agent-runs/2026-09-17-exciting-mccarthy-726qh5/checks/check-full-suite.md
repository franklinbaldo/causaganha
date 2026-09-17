---
type: AgentCheck
id: "2026-09-17-exciting-mccarthy-726qh5-check-full-suite"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
goal_id: "2026-09-17-exciting-mccarthy-726qh5-goal-djen-sample-batch18"
command: "uv run pytest -q"
result: "failed"
evidence_id: null
summary: "3 failures, all the documented transient shape from the scaffold's own caveat (test_check_agent_run_completeness.py, test_generate_okf_zod_schemas.py, test_okf_domain_models.py) caused by this round's own run.md still being in draft (completed_at/next_move/result_summary/check_ids/evidence_ids empty) at the time of this run. Everything else green. Re-run scheduled after run.md is filled in as this round closes."
---

# Check: suite completa (primeira passada, relatorio ainda em rascunho)

`uv run pytest -q` rodou a suite inteira. 3 falhas, todas com a mesma
causa documentada no proprio `.claude/agent-run-scaffold.md`: enquanto
`knowledge/agent-runs/2026-09-17-exciting-mccarthy-726qh5/run.md` ainda
tem `completed_at`/`next_move`/`result_summary`/`check_ids`/`evidence_ids`
vazios, a instancia `AgentRun` incompleta no bundle muda temporariamente
a forma inferida pelos geradores Zod/domain-model:

- `tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete`
- `tests/web/test_generate_okf_zod_schemas.py::test_generated_zod_schemas_file_matches_current_knowledge_bundle`
- `tests/causaganha_mcp/test_okf_domain_models.py::test_generated_domain_models_file_matches_current_knowledge_bundle`

Nenhum dos dois arquivos gerados (`web/src/lib/processoConsultar.gen.ts`,
`src/causaganha_mcp/_generated/domain_models.py`) precisa ser
regenerado -- os tres testes voltam a passar sozinhos assim que
`run.md` for preenchido como qualquer relatorio finalizado (ver
`check-full-suite-final.md` para a reverificacao apos o preenchimento).
Nenhuma outra falha na suite.

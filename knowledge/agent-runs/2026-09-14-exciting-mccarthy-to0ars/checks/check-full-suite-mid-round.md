---
type: AgentCheck
id: "2026-09-14-exciting-mccarthy-to0ars-check-full-suite-mid-round"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
command: "uv run pytest -q"
result: "failed"
evidence_id: "2026-09-14-exciting-mccarthy-to0ars-evidence-green-test"
summary: "Ran repo-wide while this run.md was still a draft (completed_at/primary_goal_id/result_summary/next_move empty). 3 failures, all the documented draft-AgentRun cascade the scaffold's own footnote predicts, not new bugs: tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete (this round's own run.md correctly reported incomplete -- expected, it is still a draft), tests/web/test_generate_okf_zod_schemas.py and tests/causaganha_mcp/test_okf_domain_models.py (both fail because okf-parser derives the generated Zod/domain-model schemas' optional-vs-required shape from the full knowledge bundle, and a draft AgentRun with empty fields temporarily changes that inferred shape vs. the committed generated files). All 3 are expected to self-resolve once this run.md is filled in like every other closed round -- verified below in check-full-suite-final after finishing the report; the scripts/audit_cnj_parquets.py + tests/test_audit_cnj_parquets.py changes themselves are unaffected (32/32 passed within this same run, see evidence-green-test)."
---

# Check: suíte completa em meio à rodada (run.md ainda rascunho)

3 falhas, todas o cascade documentado de `AgentRun` em rascunho (não bugs novos): o próprio gate de completude reportando este `run.md` como incompleto (correto, ainda é rascunho), e os dois testes de regeneração Zod/domain-model que dependem da forma inferida do bundle completo. Esperado que as três se resolvam sozinhas ao fechar o relatório.

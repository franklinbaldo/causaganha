---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-izm703-check-python-suite"
run_id: "2026-09-08-exciting-mccarthy-izm703"
command: "uv run pytest tests/test_render_queries.py -k double_count -v && uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "passed"
evidence_id: "2026-09-08-exciting-mccarthy-izm703-evidence-green-tests"
summary: "tests/test_render_queries.py -k double_count: 3 passed (post-fix; RED confirmed pre-fix, see evidence-red-tests.md). Full tests/test_render_queries.py: 34 passed. Full uv run pytest -q: green except test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, the one test CLAUDE.md/the scaffold document as expected to fail while this round's run.md is still mid-draft (missing completed_at/primary_goal_id/etc.) -- confirmed this is the only failure by grepping the short test summary (1 FAILED line). The two generated-schema drift tests the scaffold also warns about (tests/web/test_generate_okf_zod_schemas.py, tests/causaganha_mcp/test_okf_domain_models.py) were run in isolation and both passed (10/10) -- this round's draft frontmatter did not perturb the inferred Zod/domain-model shape. ruff check: all checks passed. ruff format --check: 394 files already formatted."
---

# Check: suite Python (testes novos + suíte completa), ruff

Testes RED->GREEN confirmados (`-k double_count`). Suíte completa: verde exceto o gate de completude do próprio `run.md` (esperado em rascunho); os dois testes de drift de schema gerado (Zod/domain models) passam isolados. `ruff check` e `ruff format --check` limpos.

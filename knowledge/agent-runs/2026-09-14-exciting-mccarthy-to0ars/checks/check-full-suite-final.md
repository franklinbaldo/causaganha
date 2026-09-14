---
type: AgentCheck
id: "2026-09-14-exciting-mccarthy-to0ars-check-full-suite-final"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
command: "uv run pytest -q && uv run ruff check . && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-14-exciting-mccarthy-to0ars-evidence-generated-files-regenerated"
summary: "After finishing the report and regenerating web/src/lib/processoConsultar.gen.ts + src/causaganha_mcp/_generated/domain_models.py (see evidence-generated-files-regenerated), re-ran the full suite: 100% green repo-wide (0 failures, includes tests/test_audit_cnj_parquets.py 32/32, tests/test_check_agent_run_completeness.py, and the two generated-file drift tests that had failed before regenerating). ruff check and ruff format --check both clean across the whole repo."
---

# Check final: suíte completa + ruff, 100% verde

`uv run pytest -q`: 0 falhas em todo o repositório, após regenerar os dois arquivos gerados que haviam ficado desatualizados (ver evidência associada). `ruff check`/`ruff format --check`: limpos.

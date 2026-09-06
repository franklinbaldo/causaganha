---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-usm2ot-check-python-suite"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
goal_id: "2026-09-06-exciting-mccarthy-usm2ot-goal-backlog-cache"
command: "uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-usm2ot-evidence-green-backlog-test"
summary: "ruff check: All checks passed. ruff format --check: clean after reformatting tests/knowledge/test_backlog.py once with `uv run ruff format`. Regenerated src/causaganha_mcp/_generated/domain_models.py (scripts/generate_okf_domain_models.py) and web/src/lib/processoConsultar.gen.ts (scripts/generate_okf_zod_schemas.py) after adding BacklogItem to the schema, since both are checked byte-for-byte against the current knowledge bundle by tests/causaganha_mcp/test_okf_domain_models.py and tests/web/test_generate_okf_zod_schemas.py. Full suite green after these steps."
---

# Check: suíte Python completa

`ruff check`, `ruff format --check` e `pytest -q` ficam verdes depois de regenerar os artefatos derivados do schema OKF (domain models Python e schemas Zod) que passaram a incluir `BacklogItem`.

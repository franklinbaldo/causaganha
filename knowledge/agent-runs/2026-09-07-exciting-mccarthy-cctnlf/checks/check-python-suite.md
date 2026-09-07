---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-cctnlf-check-python-suite"
run_id: "2026-09-07-exciting-mccarthy-cctnlf"
goal_id: "2026-09-07-exciting-mccarthy-cctnlf-goal-tribunal-list-merge"
command: "TRIBUNAL=tjro uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "passed"
summary: "Full pytest -q run fails exactly the three known mid-draft artifacts (tests/test_check_agent_run_completeness.py's own-tree check; tests/web/test_generate_okf_zod_schemas.py and tests/causaganha_mcp/test_okf_domain_models.py's generated-file drift), all caused solely by this round's own run.md still carrying empty completed_at/primary_goal_id/result_summary/next_move (independently verified in decision-mid-draft-schema-drift.md by removing this round's directory and re-running clean) — no test related to tribunais.py or any other production code fails. ruff check: all checks passed. ruff format --check: clean after auto-formatting the new test file earlier in the round. This check will be re-run after run.md is finalized to confirm all three artifacts disappear."
---

# Check: suíte Python completa + ruff

Falham só os três artefatos conhecidos de rascunho (causados pelo próprio `run.md` incompleto desta rodada, não pela mudança em `tribunais.py`). `ruff check`/`ruff format --check` limpos.

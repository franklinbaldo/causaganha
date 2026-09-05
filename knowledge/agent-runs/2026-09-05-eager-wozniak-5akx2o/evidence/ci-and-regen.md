---
type: AgentEvidence
id: "2026-09-05-eager-wozniak-5akx2o-evidence-ci-and-regen"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
kind: "ci"
reference: "uv run ruff check; uv run ruff format --check; uv run pytest tests/test_check_agent_run_completeness.py tests/causaganha_mcp tests/web/test_generate_okf_zod_schemas.py -q"
summary: "Merging PR #1141 added AgentRun (and siblings) to knowledge/okf.schema.sql with no instance yet, so tests/causaganha_mcp/test_okf_domain_models.py stayed green. Populating this round's own knowledge/agent-runs/.../ tree (run.md plus its readings/goals/decisions/evidence/checks) made scripts/generate_okf_domain_models.py/generate_okf_zod_schemas.py emit AgentRunConcept and its siblings for the first time, which put src/causaganha_mcp/_generated/domain_models.py and web/src/lib/processoConsultar.gen.ts out of date against the drift-gate tests. Re-ran both generators twice (once after run.md, again after the full report tree) to close that drift each time. Full suite after: ruff check clean, ruff format --check clean (one file auto-formatted), 30 tests passed."
---

# Evidência: checks e regeneração após instanciar o primeiro AgentRun

---
type: AgentCheck
id: "2026-09-05-eager-wozniak-5akx2o-check-full-suite-and-regen"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
command: "uv run python scripts/generate_okf_domain_models.py; uv run python scripts/generate_okf_zod_schemas.py; uv run pytest tests/test_check_agent_run_completeness.py tests/causaganha_mcp tests/web/test_generate_okf_zod_schemas.py -q"
result: "passed"
evidence_id: "2026-09-05-eager-wozniak-5akx2o-evidence-ci-and-regen"
summary: "Regenerated both generated files to include the new AgentRunConcept now that this round's run.md is a real instance under knowledge/; full suite: 30 passed."
---

# Check: suíte completa após regenerar modelos OKF

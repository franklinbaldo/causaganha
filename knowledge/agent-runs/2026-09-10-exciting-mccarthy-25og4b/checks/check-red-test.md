---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-25og4b-check-red-test"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
command: "uv run pytest -q tests/causaganha/processos/test_query_plan_fixtures.py (against original DATE-typed query_plan_fixtures.py)"
result: "failed"
evidence_id: "2026-09-10-exciting-mccarthy-25og4b-evidence-red-test"
summary: "Both new tests failed as expected against the unmodified fixture, confirming the gap: the STJ columns were DATE-typed and the ::DATE/::VARCHAR casts of dataDecisao produced the identical string."
---

# Check: teste RED

`uv run pytest -q tests/causaganha/processos/test_query_plan_fixtures.py` contra o fixture original -> 2 falhas, confirmando o gap descrito no goal.

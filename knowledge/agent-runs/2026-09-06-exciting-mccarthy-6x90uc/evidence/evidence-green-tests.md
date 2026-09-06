---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-6x90uc-evidence-green-tests"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
goal_id: "2026-09-06-exciting-mccarthy-6x90uc-goal-schema-drift-detection"
kind: "test_green"
reference: "uv run pytest tests/test_check_agent_run_completeness.py -q (after implementing declared_fields_for_type/unknown_fields_for_type and wiring main())"
summary: "43/43 passed, 0 failed — includes the 8 new tests (fully-filled sibling/run frontmatter has zero unknown fields; a renamed AgentGoal field is reported unknown while still separately reported missing under its schema name; the AgentDecision/AgentEvidence/AgentCheck optional columns goal_id/evidence_id are not false-flagged; a directory containing one drifted AgentGoal makes main() return 1) plus every pre-existing test in the module, unchanged."
---

# GREEN

43/43 testes passam no módulo, incluindo os 8 novos.

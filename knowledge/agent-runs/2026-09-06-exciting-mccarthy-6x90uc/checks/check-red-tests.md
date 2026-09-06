---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-6x90uc-check-red-tests"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
goal_id: "2026-09-06-exciting-mccarthy-6x90uc-goal-schema-drift-detection"
command: "uv run pytest tests/test_check_agent_run_completeness.py -q (before implementation)"
result: "failed"
evidence_id: "2026-09-06-exciting-mccarthy-6x90uc-evidence-red-tests"
summary: "Collection failed with ImportError for unknown_fields_for_type, confirming the RED state before any implementation."
---

# Check RED

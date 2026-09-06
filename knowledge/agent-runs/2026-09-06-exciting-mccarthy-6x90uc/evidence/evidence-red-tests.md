---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-6x90uc-evidence-red-tests"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
goal_id: "2026-09-06-exciting-mccarthy-6x90uc-goal-schema-drift-detection"
kind: "test_red"
reference: "uv run pytest tests/test_check_agent_run_completeness.py -q (before implementing unknown_fields_for_type)"
summary: "Collection error: `ImportError: cannot import name 'unknown_fields_for_type' from 'scripts.check_agent_run_completeness'` — the 8 new tests (and every pre-existing test in the module, via collection failure) fail exactly as the missing feature predicts, before any implementation exists."
---

# RED

`ImportError` na coleta: `unknown_fields_for_type` ainda não existe no módulo.

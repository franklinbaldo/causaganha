---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-usm2ot-evidence-red-backlog-test"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
goal_id: "2026-09-06-exciting-mccarthy-usm2ot-goal-backlog-cache"
kind: "test_red"
reference: "uv run pytest tests/knowledge/test_backlog.py -v (before knowledge/backlog/ existed)"
summary: "tests/knowledge/test_backlog.py was written before knowledge/backlog/ existed. 1 failed, 5 passed: test_backlog_directory_exists_and_is_nonempty failed with AssertionError ('knowledge/backlog/ must exist'), confirming the test genuinely exercises the not-yet-built directory rather than passing vacuously."
---

# RED: knowledge/backlog/ ainda não existia

`test_backlog_directory_exists_and_is_nonempty` falhou como esperado antes de o diretório existir, confirmando que o teste realmente testa algo.

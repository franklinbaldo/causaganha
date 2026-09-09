---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-v38h6d-check-red-test"
run_id: "2026-09-09-exciting-mccarthy-v38h6d"
goal_id: "2026-09-09-exciting-mccarthy-v38h6d-goal-check-only-no-io"
command: "uv run pytest tests/djen_backup/test_check_only_no_io.py -q -s"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-v38h6d-evidence-red-test"
summary: "Ran against unmodified src/djen_backup/engine.py. Failed with AssertionError: called['download'] was True when it should have stayed False -- confirming check_only=True does not currently prevent the download worker from draining an existing backlog entry, exactly as expected before the fix."
---

# Check: teste RED

Confirma que o novo teste de regressao falha contra o `engine.py` original antes da correcao.

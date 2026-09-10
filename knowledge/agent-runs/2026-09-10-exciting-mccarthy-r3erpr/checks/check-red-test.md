---
type: AgentCheck
id: "2026-09-10-exciting-mccarthy-r3erpr-check-red-test"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
goal_id: "2026-09-10-exciting-mccarthy-r3erpr-goal-cb-probe-lock-order"
command: "uv run pytest tests/djen_backup/test_circuit_breaker_lock_interaction.py -v (run against unmodified src/djen_backup/archive.py, before the guard reorder)"
result: "failed"
evidence_id: "2026-09-10-exciting-mccarthy-r3erpr-evidence-red-test"
summary: "test_item_busy_does_not_consume_half_open_probe: AssertionError, breaker.state == CircuitState.OPEN, expected HALF_OPEN. Confirms the bug: the half-open probe was consumed by a call that raised ItemBusyError before ever attempting the IA upload."
---

# Check: teste RED antes da correção

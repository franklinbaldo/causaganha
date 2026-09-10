---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-r3erpr-evidence-red-test"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
goal_id: "2026-09-10-exciting-mccarthy-r3erpr-goal-cb-probe-lock-order"
kind: "test_red"
reference: "tests/djen_backup/test_circuit_breaker_lock_interaction.py::test_item_busy_does_not_consume_half_open_probe, run via `uv run pytest tests/djen_backup/test_circuit_breaker_lock_interaction.py -v` against unmodified src/djen_backup/archive.py (guard order: circuit breaker allow_request() before the try_lock check)."
summary: "Failed with AssertionError: breaker.state == CircuitState.OPEN, expected CircuitState.HALF_OPEN -- confirming allow_request() consumed the half-open probe even though the subsequent try_lock check immediately raised ItemBusyError without ever attempting the IA upload."
---

# Evidência RED

`uv run pytest tests/djen_backup/test_circuit_breaker_lock_interaction.py -v` no código original: `AssertionError: assert <CircuitState.OPEN: 'open'> == <CircuitState.HALF_OPEN: 'half_open'>`. Confirma que `allow_request()` consumiu o probe HALF_OPEN mesmo com o item ocupado e o upload nunca tentado.

---
type: "RunEvidence"
id: "run-evidence/20260910t082643z-do-the-best-useful-work-availab/evidence-red-then-green-diff"
run: "runs/20260910T082643Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/common/test_relay.py; src/common/relay.py"
summary: "RED: added test_relay_module_surface_excludes_async_transport asserting common.relay has no AsyncRelayTransport/async_relay_transport_from_env attributes; ran 'uv run pytest tests/common/test_relay.py -q' and it failed (AssertionError: assert not True) while the dead code was still present. GREEN: deleted the AsyncRelayTransport class and async_relay_transport_from_env function from src/common/relay.py and the three async-specific tests that imported them from tests/common/test_relay.py; re-ran the same command and all 6 tests passed."
goal: "run-goals/20260910t082643z-do-the-best-useful-work-availab/goal-remove-dead-async-relay-transport"
---

# RunEvidence

---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-5pnpmt-check-python-relay-tests"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
evidence_id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-green-python-relay"
command: "uv run pytest tests/deployment/relay/test_main.py tests/common/test_relay.py tests/test_deployment_hygiene.py"
result: "passed"
summary: "46 + 8 + 8 = suites completas verdes apos a correcao do relay Python: tests/deployment/relay/test_main.py (46 passed), tests/common/test_relay.py (8 passed, cliente RelayTransport inalterado), tests/test_deployment_hygiene.py (8 passed, nenhuma regressao de higiene de deploy)."
---

# Check: suites Python do relay

```
$ uv run pytest tests/deployment/relay/test_main.py
46 passed in 0.18s

$ uv run pytest tests/common/test_relay.py tests/test_deployment_hygiene.py
8 passed in 0.07s
```

---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-green-python-relay"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
kind: "test_green"
reference: "deployment/relay/function/main.py; tests/deployment/relay/test_main.py"
summary: "uv run pytest tests/deployment/relay/test_main.py: 46 passed apos a correcao. main.py agora: rejeita esquema != https (403); restringe metodo a GET/HEAD/POST (405 para o resto); remove Authorization/Cookie do encaminhamento e Set-Cookie da resposta (_STRIP_HEADERS/_RESPONSE_STRIP_HEADERS); aplica _MAX_REQUEST_BODY_BYTES=10MiB (413 se excedido) e _MAX_RESPONSE_BYTES=25MiB via streaming com abort antecipado (_client.stream + iter_bytes, 502 se excedido antes de materializar a resposta inteira em memoria)."
---

# Evidencia GREEN: relay Python com politica de egress (TM-02/#1609)

```
$ uv run pytest tests/deployment/relay/test_main.py
..............................................                           [100%]
46 passed in 0.18s
```

Tambem confirmado: `uv run pytest tests/common/test_relay.py
tests/test_deployment_hygiene.py` (8 passed) e `uv run ruff check
deployment/relay/ tests/deployment/relay/ && uv run ruff format
--check deployment/relay/ tests/deployment/relay/` (All checks
passed! / 3 files already formatted) sem regressao.

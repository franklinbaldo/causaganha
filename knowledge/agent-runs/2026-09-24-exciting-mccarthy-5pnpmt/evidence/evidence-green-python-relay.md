---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-green-python-relay"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
kind: "test_green"
reference: "deployment/relay/function/main.py; tests/deployment/relay/test_main.py"
summary: "SUPERSEDIDO apos merge de conflito com origin/main -- ver decision-resolve-merge-conflict-concurrent-tm02-work. Enquanto esta rodada trabalhava, uma sessao Wisk concorrente mesclou PR #1625 fechando a mesma lacuna (HTTPS-only, metodo GET/HEAD/POST, Authorization/Cookie, budgets de tamanho) com constantes/nomes diferentes (MAX_REQUEST_BODY_BYTES=5MiB/MAX_RESPONSE_BODY_BYTES=50MiB, publicas, sem underscore). Ao resolver o conflito de merge em deployment/relay/function/main.py, esta rodada adotou a versao ja mesclada de #1625 em vez de reescrever por cima -- o diff abaixo (46 passed, _MAX_REQUEST_BODY_BYTES/_MAX_RESPONSE_BYTES) descreve fielmente o que esta rodada implementou e validou ANTES do conflito, mas nao e mais o que esta no main.py final desta PR. O unico gap que sobreviveu a reconciliacao (Set-Cookie da resposta) tem evidencia propria em evidence-red-green-set-cookie-python-relay."
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

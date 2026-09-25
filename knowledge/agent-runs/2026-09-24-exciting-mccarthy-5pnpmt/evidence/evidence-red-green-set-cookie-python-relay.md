---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-red-green-set-cookie-python-relay"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
kind: "test_red"
reference: "deployment/relay/function/main.py (apos merge de origin/main, PR #1625 ja incorporada); tests/deployment/relay/test_main.py::test_relay_strips_set_cookie_from_upstream_response"
summary: "Apos reconciliar com o main.py ja mesclado por PR #1625 (que fechou HTTPS-only/metodo/Authorization-Cookie/budgets de tamanho, mas nao tocou Set-Cookie da resposta), rodar tests/deployment/relay/test_main.py::test_relay_strips_set_cookie_from_upstream_response contra esse main.py mesclado confirmou RED (AssertionError: 'set-cookie' presente nos headers devolvidos ao chamador -- _RESPONSE_STRIP_HEADERS de #1625 so tinha content-encoding alem do _STRIP_HEADERS base). Corrigido adicionando 'set-cookie' a _RESPONSE_STRIP_HEADERS; GREEN confirmado: suite inteira do modulo (tests/deployment/relay/test_main.py) 42/42 (41 de #1625 + este)."
---

# Evidencia RED->GREEN: Set-Cookie no relay Python (gap remanescente pos-merge)

```
$ uv run pytest tests/deployment/relay/test_main.py -k set_cookie -v
FAILED tests/deployment/relay/test_main.py::test_relay_strips_set_cookie_from_upstream_response
AssertionError: assert 'set-cookie' not in {'set-cookie': 'session=abc123', ...}

# apos adicionar "set-cookie" a _RESPONSE_STRIP_HEADERS:
$ uv run pytest tests/deployment/relay/test_main.py -v
42 passed in 0.24s
```

Este e o unico gap real que sobrou no relay Python depois de
reconciliar com `#1625` (ja mesclada por uma sessao concorrente
enquanto esta rodada trabalhava) -- nem `#1625` nem nenhuma outra PR
concorrente havia tocado o stripping de `Set-Cookie` da resposta
upstream.

---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-5pnpmt-evidence-red-python-relay"
run_id: "2026-09-24-exciting-mccarthy-5pnpmt"
goal_id: "2026-09-24-exciting-mccarthy-5pnpmt-goal-relay-egress-policy"
kind: "test_red"
reference: "tests/deployment/relay/test_main.py (13 novos casos adicionados nesta rodada)"
summary: "Ainda valido como demonstracao do estado ORIGINAL (pre-#1608/#1609) do relay Python -- mas a correcao que esta rodada implementou a partir daqui foi descartada ao resolver um conflito de merge com uma PR concorrente (#1625) que fechou a mesma lacuna primeiro; ver decision-resolve-merge-conflict-concurrent-tm02-work e evidence-green-python-relay. uv run pytest tests/deployment/relay/test_main.py contra o deployment/relay/function/main.py original (antes de qualquer mudanca de producao): 13 dos 46 casos falharam, confirmando RED. Falhas: test_relay_rejects_plain_http_to_allowlisted_host (http:// para host allowlistado hoje retorna 200/upstream em vez de 403 -- so esquemas fora de {http,https} eram rejeitados); test_relay_rejects_disallowed_methods[PUT/PATCH/DELETE/TRACE/CONNECT/OPTIONS] (6 casos -- hoje qualquer metodo passa direto ao upstream); test_forward_headers_strips_authorization_and_cookie (Authorization/Cookie hoje sao encaminhados ao upstream); test_relay_strips_set_cookie_from_upstream_response (Set-Cookie da resposta upstream hoje volta ao chamador); test_relay_rejects_oversized_request_body, test_relay_allows_request_body_within_budget, test_relay_rejects_oversized_upstream_response, test_relay_allows_upstream_response_within_budget (4 casos -- AttributeError, _MAX_REQUEST_BODY_BYTES/_MAX_RESPONSE_BYTES nao existiam no modulo)."
---

# Evidencia RED: relay Python sem politica de egress (TM-02/#1609)

```
$ uv run pytest tests/deployment/relay/test_main.py
..............................FFFFFFF...FFFFFF                           [100%]
=== 13 failed, 33 passed ===
```

Confirma ao vivo, antes de qualquer mudanca de producao, que o relay
Python (`deployment/relay/function/main.py`) aceitava `http://` para
hosts allowlistados, nao restringia metodo HTTP, encaminhava
`Authorization`/`Cookie` ao upstream e `Set-Cookie` de volta ao
chamador, e nao tinha nenhum teto de tamanho de corpo de requisicao
ou resposta.

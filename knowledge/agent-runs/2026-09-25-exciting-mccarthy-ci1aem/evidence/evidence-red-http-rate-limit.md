---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-ci1aem-evidence-red-http-rate-limit"
run_id: "2026-09-25-exciting-mccarthy-ci1aem"
goal_id: "2026-09-25-exciting-mccarthy-ci1aem-goal-mcp-http-rate-limit"
kind: "test_red"
reference: "tests/causaganha_mcp/test_http_rate_limit.py"
summary: "10 testes novos escritos primeiro contra a API alvo (HttpSettings.rate_limit_per_minute, OperationalLimitsMiddleware(rate_limit_per_minute=..., rate_limit_window_seconds=...)), que ainda nao existia. `uv run pytest -q tests/causaganha_mcp/test_http_rate_limit.py` falhou com 10/10 -- os 4 testes de HttpSettings falharam por AssertionError/ValueError nao levantado (o campo rate_limit_per_minute nao existia, entao HttpSettings.from_env() simplesmente ignorava a variavel de ambiente nova); os 6 testes de OperationalLimitsMiddleware falharam todos com AttributeError ('causaganha_mcp.http_server' has no attribute 'get_http_request') ao tentar fazer monkeypatch.setattr(http_entry, 'get_http_request', ...) -- confirmando que o proprio import/simbolo usado para identificar o cliente nao existia antes da mudanca, nao so o comportamento de rate limit."
---

# Evidencia RED: rate limit por cliente ainda nao existe

`tests/causaganha_mcp/test_http_rate_limit.py` escrito primeiro contra a
API alvo do objetivo desta rodada. Rodado contra o codigo original (antes
de qualquer mudanca em `src/causaganha_mcp/http_server.py`): 10/10 testes
falharam, confirmando ausencia total do rate limit por cliente antes da
implementacao -- nao apenas do comportamento de rejeicao, mas do proprio
mecanismo de identificacao de cliente (`get_http_request` nao era
importado/usado em `http_server.py`).

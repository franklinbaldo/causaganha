---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-ci1aem-evidence-green-http-rate-limit"
run_id: "2026-09-25-exciting-mccarthy-ci1aem"
goal_id: "2026-09-25-exciting-mccarthy-ci1aem-goal-mcp-http-rate-limit"
kind: "test_green"
reference: "tests/causaganha_mcp/test_http_rate_limit.py, tests/causaganha_mcp/test_http_transport.py"
summary: "Apos implementar HttpSettings.rate_limit_per_minute (com CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE, default 120, 0 desliga), OperationalLimitsMiddleware._client_key/_check_rate_limit/_raise_if_over_budget (janela fixa por chave de cliente, poda oportunista alem de _MAX_TRACKED_RATE_LIMIT_CLIENTS) e a passagem do setting em main(): `uv run pytest -q tests/causaganha_mcp/test_http_rate_limit.py tests/causaganha_mcp/test_http_transport.py` -- 26/26 verde (10 novos + 3 testes pre-existentes de HttpSettings/entrypoint estendidos com o novo campo, sem quebrar nenhum caso anterior). `uv run pytest -q tests/causaganha_mcp/` (suite completa do modulo MCP) -- 100% verde exceto tests/causaganha_mcp/test_okf_domain_models.py::test_generated_domain_models_file_matches_current_knowledge_bundle, a falha esperada e auto-resolvivel ja documentada no scaffold enquanto este proprio run.md permanece em rascunho; nenhuma outra tool/perfil do MCP regrediu."
---

# Evidencia GREEN: rate limit por cliente implementado

Todos os 10 testes novos passam apos a implementacao; os 3 testes
pre-existentes de `HttpSettings`/entrypoint que precisaram ser estendidos
com o novo campo (`rate_limit_per_minute`) tambem passam. A suite
completa de `tests/causaganha_mcp/` (250 testes) permanece 100% verde,
confirmando ausencia de regressao em qualquer outra tool ou perfil do
MCP.

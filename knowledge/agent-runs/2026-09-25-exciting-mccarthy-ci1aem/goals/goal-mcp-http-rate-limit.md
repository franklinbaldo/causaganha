---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-ci1aem-goal-mcp-http-rate-limit"
run_id: "2026-09-25-exciting-mccarthy-ci1aem"
goal: "Fechar a fatia TM-06 de #950 (security/product: MCP publico): impor um limite de chamadas por cliente (por IP/X-Forwarded-For) na superficie HTTP publica do MCP (src/causaganha_mcp/http_server.py), alem do timeout/concorrencia global ja existentes em OperationalLimitsMiddleware."
rationale: "docs/SECURITY_THREAT_MODEL.md (TM-06) documenta explicitamente a lacuna: 'http_server.py ja define timeout e concorrencia global; modelos limitam paginacao/resultados. Nao ha rate limit por origem/token no servidor publico.' Um unico chamador sequencial ainda pode consumir toda a fatia de concorrencia global (4) e toda a banda/timeout budget disponivel, negando o servico a outros clientes -- flood sequencial de um unico IP nao e barrado por nenhum controle hoje. E self-contained (um unico modulo, sem credenciais externas), nao depende de decisao de infraestrutura de deploy real (quotas na camada de deploy continuam fora do escopo, documentadas como follow-up), e tem precedente direto no proprio arquivo (OperationalLimitsMiddleware ja existe e ja tem suite de testes em tests/causaganha_mcp/test_http_transport.py para estender)."
success_signal: "tests/causaganha_mcp/test_http_transport.py (ou um novo arquivo irmao) ganha casos que RED-confirmam contra o codigo anterior (nenhum rate limit por cliente existe -- N chamadas do mesmo IP nunca sao rejeitadas) e GREEN-confirmam apos a correcao: (1) um cliente que excede rate_limit_per_minute dentro da janela recebe ToolError distinguivel de saturacao/timeout; (2) um segundo cliente (IP diferente) continua servido normalmente enquanto o primeiro esta limitado (bucket por chave, nao global); (3) a janela reseta apos o periodo configurado, liberando o cliente; (4) X-Forwarded-For (primeiro hop) e usado quando presente, senao request.client.host; (5) rate_limit_per_minute=None desliga o controle (comportamento antigo preservado, sem regressao para quem nao configurar nada de diferente do padrao); (6) chamadas fora de um contexto HTTP real (get_http_request() levanta RuntimeError) nao quebram a chamada -- caem num bucket de fallback em vez de propagar excecao nao tratada. HttpSettings.from_env() ganha CAUSAGANHA_MCP_RATE_LIMIT_PER_MINUTE com default>0 documentado. uv run pytest -q tests/causaganha_mcp/ fica verde; uv run ruff check/format --check limpos; uv run pytest -q (suite completa do repositorio) sem nenhuma regressao nova."
status: "achieved"
---

# Objetivo: rate limit por cliente no transporte HTTP publico do MCP (TM-06/#950)

Trabalho principal desta rodada. Fecha a lacuna que a propria matriz do
threat model ja nomeia: o MCP publico bound global de concorrencia/timeout
existe, mas nenhum controle impede um unico chamador sequencial de
monopolizar esse budget e negar servico aos demais. Ver
`decision_ids`/`evidence_ids`/`check_ids` para o processo TDD completo.

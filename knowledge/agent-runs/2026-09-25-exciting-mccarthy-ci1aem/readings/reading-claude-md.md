---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-ci1aem-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-ci1aem"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. O trabalho selecionado (rate limiting por cliente no transporte HTTP publico do MCP, src/causaganha_mcp/http_server.py) fica fora da fronteira djen-backup/manifesto (nao toca sync-manifest.parquet/djen_raw) e fora da fronteira CSS/Panda (nao e frontend). Regra de estilo relevante: 'No blind except Exception' -- o codigo novo nao precisa capturar Exception ampla em lugar nenhum (o unico ponto sensivel, get_http_request() fora de um request HTTP real, levanta RuntimeError especifico, tratado com except RuntimeError, nao Exception). TRY300/TRY301/TRY401: revisado ao escrever _check_rate_limit para nao violar (raise direto, sem try ao redor do proprio raise). Python 3.12+/'|' unions/'from __future__ import annotations' ja presentes no arquivo alvo. Rodar 'uv run ruff check'/'uv run ruff format --check'/'uv run pytest -q' antes de abrir PR, conforme secao 'Before committing'."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada. Nenhuma regra
bloqueia ou reorienta o trabalho escolhido (rate limiting por cliente no
`http_server.py` publico do MCP) -- e Python puro, sem `boto3`, sem cache
JSON gerado de fonte aleatoria, sem tocar `archive.py`/manifesto. A regra
de "no blind except Exception" e observada explicitamente ao tratar a
ausencia de contexto HTTP real (`RuntimeError` especifico de
`get_http_request()`, nunca `except Exception`).

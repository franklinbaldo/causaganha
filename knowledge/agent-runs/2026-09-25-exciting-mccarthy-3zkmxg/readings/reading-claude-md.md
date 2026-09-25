---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-3zkmxg-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. sync-manifest.parquet (IA) e a fonte da verdade do djen-backup; djen_raw e apenas o codigo de transporte HTTP, nunca um veredito de disponibilidade (200 sem URL de download = absent, igual a 404); 403 nunca e absent (rate limit de WAF/CloudFront). Fronteira Panda/Svelte: novas paginas usam css()/recipes do preset cobogo, tres ilhas Svelte legadas (ProcessoLookup, PublicationSearch, SavedConsultations) continuam com --papel-*/--s-* e scoped <style>. Estilo Python: ruff estrito, TRY300/TRY301/TRY401 aplicados, sem except Exception generico fora do bulkhead da ADR 0011, from __future__ import annotations no topo, uv run ruff check/format --check + uv run pytest -q antes de commitar. O trabalho selecionado nesta rodada (issue #1611, budgets de recursos em src/causaganha/consolidate/zip_processor.py contra decompression bombs e downloads sem teto) e puro Python neste arquivo listado explicitamente no mapa de arquivos como parte do backend de consolidacao -- respeita TRY301 (raise extraido para funcao interna _raise_too_large em download_zip), nao usa except Exception generico (excecoes especificas: ZipBudgetExceededError(ValueError)/DownloadTooLargeError(OSError), capturadas por tipo especifico nos callers) e nao toca a fronteira CSS/Panda nem o sync-manifest."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme exigido
pelo contrato `AgentRun`. Nenhuma regra bloqueia ou orienta diretamente o
trabalho escolhido (budgets de ingestao contra bombas de descompressao em
`zip_processor.py`), mas as regras de estilo Python (TRY301, tipos de
excecao especificos, `ruff`/`pytest` antes de commitar) foram seguidas
durante a implementacao.

---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-0lqpmv-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Backend em src/causaganha e src/djen_backup, frontend em web/ (Astro+Svelte). sync-manifest.parquet no IA é a fonte de verdade de coleta (djen_raw é o HTTP status bruto, djen_status é o veredito derivado; um 200 sem download_url no corpo é 'ausente', não 'disponível' -- nunca equiparar os dois). Estilo: ruff estrito (TRY300/301/401 obrigatórios), sem except Exception amplo fora do bulkhead documentado em ADR 0011, Python 3.12+ com `from __future__ import annotations`. Fronteira de tokens CSS: Panda via preset cobogo é o único sistema; index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas (ProcessoLookup/PublicationSearch/SavedConsultations). Antes de commitar: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nenhuma seção de CLAUDE.md trata de build/empacotamento Python nem do Dockerfile do MCP -- não há orientação explícita sobre lockfile/reprodutibilidade de build ali; essa lacuna é coberta pela issue #1614 (ver reading-issues)."
---

# Leitura: CLAUDE.md

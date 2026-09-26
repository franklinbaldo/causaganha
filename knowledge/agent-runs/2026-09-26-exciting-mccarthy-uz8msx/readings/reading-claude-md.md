---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-uz8msx-reading-claude-md"
run_id: "2026-09-26-exciting-mccarthy-uz8msx"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Backend em src/causaganha e src/djen_backup, frontend em web/ (Astro 7 + Svelte 5). sync-manifest.parquet no IA é a fonte de verdade de coleta (djen_raw = HTTP status bruto, djen_status = veredito derivado; 200 sem download_url é 'ausente', não 'disponível'; 403 nunca é ausente). Contratos de query do frontend vivem em web/src/queries/*.qmd + web/src/lib/data/contracts.ts. Regras de estilo: ruff estrito, TRY300/TRY301/TRY401, sem except Exception amplo fora do bulkhead documentado em ADR 0011, Python 3.12+ com `from __future__ import annotations`. Fronteira CSS: Panda via preset cobogo é o sistema único; web/src/index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas. Antes de commitar: uv run ruff check, uv run ruff format --check, uv run pytest -q. Nenhuma seção nova relevante para o trabalho desta rodada além do já internalizado por rodadas anteriores."
---

# Leitura: CLAUDE.md

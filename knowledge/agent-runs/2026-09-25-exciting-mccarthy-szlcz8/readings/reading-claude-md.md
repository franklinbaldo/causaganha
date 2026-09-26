---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-szlcz8-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-szlcz8"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Backend em src/causaganha e src/djen_backup, frontend em web/. sync-manifest.parquet no IA é a fonte de verdade de coleta (djen_raw = HTTP status bruto, djen_status = veredito derivado; 200 sem download_url é 'ausente', não 'disponível'; 403 nunca é ausente). Contratos de query do frontend vivem em web/src/queries/*.qmd + web/src/lib/data/contracts.ts. Regras de estilo: ruff estrito, TRY300/TRY301/TRY401, sem except Exception amplo fora do bulkhead documentado em ADR 0011 (worker-pool loop sobre unidades independentes, com .exception() antes de registrar falha por item), Python 3.12+ com `from __future__ import annotations`. Fronteira de tokens CSS: Panda via preset cobogo é o sistema único; web/src/index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas (ProcessoLookup/PublicationSearch/SavedConsultations) que ainda usam --papel-*/--s-*; Panda's `include` nunca escaneia .svelte. Antes de commitar: uv run ruff check, uv run ruff format --check, uv run pytest -q."
---

# Leitura: CLAUDE.md

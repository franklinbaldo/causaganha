---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-o3ubcj-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Backend em src/causaganha e src/djen_backup, frontend em web/ (Astro 7 + Svelte 5). sync-manifest.parquet no IA é a fonte de verdade de coleta (djen_raw = HTTP status bruto, djen_status = veredito derivado; 200 sem download_url é 'ausente', não 'disponível'; 403 nunca é ausente). Fronteira de tokens CSS: Panda via preset cobogo é o sistema único de estilo; index.css é ponte de compatibilidade só para as 3 ilhas Svelte legadas (ProcessoLookup, PublicationSearch, SavedConsultations) -- Panda não escaneia .svelte, então css() cru dentro de um componente Svelte é não confiável. Regras de estilo: ruff estrito, TRY300/301/401, sem except Exception amplo fora do bulkhead documentado em ADR 0011, Python 3.12+, `from __future__ import annotations`. Antes de commitar: ruff check, ruff format --check, pytest -q."
---

# Leitura: CLAUDE.md

---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-qn6gvy-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Backend em src/causaganha e src/djen_backup, frontend em web/. sync-manifest.parquet no IA é a fonte de verdade de coleta (djen_raw = HTTP status bruto, djen_status = veredito derivado; 200 sem download_url é 'ausente', não 'disponível'). Regras de estilo: ruff estrito, TRY300/301/401, sem except Exception amplo fora do bulkhead documentado em ADR 0011, Python 3.12+. Fronteira de tokens CSS: Panda via preset cobogo é o sistema único; index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas. Antes de commitar: ruff check, ruff format --check, pytest -q."
---

# Leitura: CLAUDE.md

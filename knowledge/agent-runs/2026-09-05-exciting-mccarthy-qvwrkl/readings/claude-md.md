---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-qvwrkl-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup (src/djen_backup) with sync-manifest.parquet on IA as sole canonical source (djen_raw is the raw HTTP transport code only, never a verdict — 200-with-no-download-URL is genuinely absent, same as 404/400; 403 is rate-limiting and must never be treated as absent), and the web frontend (Astro 5 + Svelte 5) whose aggregate data comes from .qmd query contracts rendered by scripts/render_queries.py. Neither surface is touched by djen-backup operational work this round. Ruff is strict (no blind except Exception, TRY300/301/401) and the pre-commit gate for Python is ruff check, ruff format --check, pytest -q; the web/ frontend has its own vitest/eslint/astro-check gates not listed here but established by prior rounds' reports. CSS token boundary: Brazilian Modernism tokens (--s-*, --papel-*, --tinta-*) stay confined to homepage/marketing; semantic tokens (--color-*, --space-*, --pico-*) are for functional/data pages like /publicacoes."
---

# Leitura de CLAUDE.md

Confirma as invariantes do pipeline djen-backup (não centrais a esta rodada) e localiza o contrato de dados do frontend (.qmd -> contracts.ts) e a fronteira de tokens CSS relevante para qualquer alteração em `/publicacoes`, a superfície tocada nesta rodada.

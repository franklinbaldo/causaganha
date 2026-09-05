---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-1a1ih8-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md (full file, this session's system context)"
finding: "Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web/ (Astro 5 + Svelte 5). The djen_backup-specific correctness rules (403≠absent, 200-without-URL=absent, djen_raw as transport code not verdict, sync-manifest.parquet as sole source of truth) govern the sync engine domain, not the web product-hierarchy work this round targets. The CSS token boundary rule matters directly: '/publicacoes' is a container-layout data page, so it must stay on semantic tokens (--color-*/--space-*/--pico-*) and never pull in Brazilian Modernism tokens (--s-*/--papel-*/--tinta-*), which are reserved for the homepage/marketing surfaces (index.astro, sobre.astro). Style rules for Python (ruff strict, no blind except Exception, TRY300/301/401) are not touched by this round's work, which is confined to a single Astro page (web/src/pages/publicacoes/index.astro) plus a new colocated Vitest test — no Python files are in scope. Before committing: `uv run ruff check` / `uv run ruff format --check` / `uv run pytest -q` for Python (unaffected, but re-run for regression safety); the web equivalent, established by prior rounds' evidence rather than CLAUDE.md itself, is `cd web && npx vitest run`, `npm run lint`, `npm run typecheck`."
---

# Leitura de CLAUDE.md

Confirma que este round trabalha inteiramente em `web/src/pages/publicacoes/index.astro` (Astro, superfície de dados com layout `container`) — logo a regra da fronteira de tokens CSS (`--color-*`/`--space-*`, nunca `--s-*`/`--papel-*`/`--tinta-*`) se aplica e será respeitada por não introduzir nenhum estilo novo além do já existente na página. As regras de `djen_backup` (sync-manifest, `djen_raw`/`djen_status`) e de estilo Python não se aplicam a este diff, mas os comandos de verificação de ambos os stacks serão rodados por segurança de regressão.

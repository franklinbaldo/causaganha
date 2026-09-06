---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-uwm65t-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces documented (djen-backup sync engine, web/ Astro+Svelte). This round's selected work is web-only (web/src/pages/agentes.astro plus a new small Svelte island) and touches neither djen_backup's manifest/DJEN-status rules nor any .qmd query contract, so those correctness rules do not apply. The CSS token boundary section is directly relevant: it requires new Svelte components to style through global element-level tokens/utility classes plus a scoped <style> block with literal values (the pattern already used by web/src/components/McpConfigCard.svelte), never a raw css() call inside a .svelte file (Panda's include never scans .svelte) and never a bespoke custom property outside panda.config.ts. 'Before committing' gates (ruff check, ruff format --check, pytest -q) apply because Python contract tests are added under tests/causaganha_mcp/; web's own gates (npm run lint, npm run typecheck, npm run test) apply because production .astro/.svelte files change."
---

# Leitura de CLAUDE.md

Trabalho desta rodada é só web (`web/src/pages/agentes.astro` + um novo componente Svelte pequeno), não toca `djen_backup` nem contratos `.qmd`. A seção de fronteira de tokens CSS é a mais relevante: novo componente Svelte deve reutilizar tokens globais já expostos por `index.css` (`--border`, `--font-mono`, `--fg-muted`, `--cg-info`, ...) num `<style>` escopado com valores literais, no mesmo padrão de `McpConfigCard.svelte` — nunca `css()` dentro de `.svelte`, nunca uma custom property nova fora de `panda.config.ts`. Gates de commit: `ruff check`/`ruff format --check`/`pytest -q` (novos testes Python em `tests/causaganha_mcp/`) e os gates do `web/` (`npm run lint`, `npm run typecheck`, `npm run test`).

---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-s5c21a-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-s5c21a"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (untouched this round) and web/ (Astro 5 + Svelte 5) fed by .qmd query contracts under web/src/queries/. The djen-backup correctness rules (djen_raw vs djen_status, 403≠absent, per-item IA lock) are not implicated by this round's candidate work. CLAUDE.md's 'CSS token boundary' section (Brazilian Modernism --s-*/--papel-*/--tinta-* for homepage/marketing only vs. semantic --color-*/--space-*/--pico-* for data pages) is confirmed still stale, as flagged by the prior round (6tcxrn reading): live grep of web/src shows --pico-* is gone entirely, and --s-*/--papel-*/--tinta-* are now global compatibility aliases in web/src/index.css (e.g. `--papel-00: var(--cg-canvas)`) consumed directly inside Svelte-island <style> blocks (SavedConsultations.svelte, ProcessoLookup.svelte, PublicationSearch.svelte, TribunalCalendar.svelte) rather than confined to index.astro/sobre.astro as the rule describes — a documentation-drift item, not fixed this round since it doesn't block the selected goal. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`, plus `uv run okf-parser check knowledge --relational-schema okf.schema.sql`."
---

# Leitura de CLAUDE.md

Nenhuma regra do motor djen-backup é tocada nesta rodada — o trabalho é inteiramente em `web/`. A seção de fronteira CSS permanece desatualizada (achado já registrado por uma rodada anterior): os tokens `--s-*`/`--papel-*` sobrevivem como aliases de compatibilidade globais usados dentro de `<style>` de componentes Svelte, não apenas em `index.astro`/`sobre.astro`. Não é o alvo desta rodada, mas fica registrado como candidato de documentação para uma rodada futura.

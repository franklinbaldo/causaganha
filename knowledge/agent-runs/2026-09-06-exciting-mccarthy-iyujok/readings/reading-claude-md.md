---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-iyujok-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-iyujok"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "This round's work touches only one Svelte component (web/src/components/McpConfigCard.svelte) plus a new co-located Vitest contract test — no djen_backup manifest/DJEN-status code and no .qmd query contract, so those correctness rules do not apply. The CSS token boundary section applies regardless of whether a Svelte component is one of the four named legacy islands: 'every Svelte component in the tree, legacy or not, styles through global element-level CSS/utility classes (index.css) and its own scoped <style> block rather than css()' because Panda's include never scans .svelte files — confirmed the fix keeps the existing scoped <style> block, adds no new custom property, and does not import css(). 'Before committing' gates apply: ruff check/format and pytest -q (repo-wide; unaffected since no Python file changed) and web's own gates (npm run lint, npm run typecheck, npm run test)."
---

# Leitura de CLAUDE.md

Trabalho desta rodada é um componente Svelte isolado (`McpConfigCard.svelte`) mais um novo teste de contrato Vitest — não toca `djen_backup` nem `.qmd`. A fronteira de tokens CSS se aplica a todo componente Svelte, legado ou não: manter `<style>` escopado, sem `css()` nem custom property nova. Gates de "antes de commitar" seguem valendo (`ruff`/`pytest -q` inalterados; `npm run lint`/`typecheck`/`test`).

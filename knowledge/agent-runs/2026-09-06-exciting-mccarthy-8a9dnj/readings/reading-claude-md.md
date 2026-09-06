---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-8a9dnj-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (src/djen_backup, manifest.parquet as sole source of truth) and web/ (Astro 5 + Svelte 5, Panda CSS via the cobogo preset). This round's selected work touches only web/src/components/TribunalCoverageExplorer.svelte and its test file — a Svelte island that already follows the documented pattern (scoped <style> block, no bespoke css() calls, no --pico-*/--tinta-* tokens). No djen_raw/djen_status logic, no query-contract (.qmd) change, no IA upload code touched. 'Before committing' gates apply: ruff check/format (unaffected, no Python production code changed) and the web equivalents this repo runs for web/ changes (npm run lint, npm run typecheck, npm test) — all confirmed green live this round after `npm ci`."
---

# Leitura de CLAUDE.md

Dois runtimes documentados, nenhum tocado no núcleo Python. O trabalho fica inteiramente em `web/src/components/TribunalCoverageExplorer.{svelte,test.ts}`, um island Svelte que já segue o padrão descrito (sem CSS bespoke, sem tokens retirados). Gates aplicáveis: `ruff check`/`format` (Python, inalterado) e `npm run lint`/`typecheck`/`test` (web, verificados verdes nesta rodada).

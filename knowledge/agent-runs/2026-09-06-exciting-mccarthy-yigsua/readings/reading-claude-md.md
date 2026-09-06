---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-yigsua-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (src/djen_backup) and web/ (Astro 5 + Svelte 5) fed by .qmd query contracts rendered by scripts/render_queries.py. None of the djen-backup correctness rules (djen_raw vs djen_status, 403≠absent, per-item IA lock, sync-manifest.parquet as sole source of truth) are implicated this round — this round's candidate work is entirely in web/src/components/DuckDBExplorer.svelte, a Svelte island already outside the CSS-migration scope (it uses no --papel-*/--s-* legacy tokens), so the '### CSS token boundary' section (corrected by round ttdopu, PR #1185, and reverified unchanged by round sk8ec6) is not in play either. Live grep confirmed the section still correctly describes the single-Panda-CSS-system architecture. Gates to run before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q` (Python side, unaffected by this round unless touched); `npx vitest run` and `npx astro check` (web side); plus `uv run okf-parser check knowledge --relational-schema okf.schema.sql` and `uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs` for this round's own OKF report."
---

# Leitura de CLAUDE.md

Dois runtimes: `djen-backup` (Python) e `web/` (Astro+Svelte). Nenhuma regra de correção do `djen-backup` é relevante para o trabalho desta rodada, que fica inteiramente em `DuckDBExplorer.svelte`. A fronteira `### CSS token boundary` permanece correta (verificada por duas rodadas anteriores) e não é relevante para este componente, que não usa tokens legados. Gates antes de commitar: `ruff check`/`ruff format --check`/`pytest -q` (Python, se tocado) e `vitest run`/`astro check` (web), além do `okf-parser check` e do checker de completude dos relatórios.

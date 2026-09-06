---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-sk8ec6-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (src/djen_backup) and web/ (Astro 5 + Svelte 5) fed by .qmd query contracts rendered by scripts/render_queries.py. None of the djen-backup correctness rules (djen_raw vs djen_status, 403≠absent, per-item IA lock, sync-manifest.parquet as sole source of truth) are implicated by this round's candidate work, which is entirely in web/. Verified the '### CSS token boundary' section (CLAUDE.md:69-73), which four prior rounds independently found stale and the round ttdopu finally corrected (PR #1185): it currently and correctly describes a single Panda CSS design system via the `cobogo` preset, with web/src/index.css as a compatibility-alias bridge consumed only by four named Svelte islands (ProcessoLookup.svelte, PublicationSearch.svelte, SavedConsultations.svelte, TribunalCalendar.svelte); no --pico-*/--tinta-* references remain live grep-verified. This round's actual work item (issue #1193, DuckDBExplorer.svelte) touches none of those four legacy-alias components — it is a Svelte island already outside the CSS-migration scope entirely (its own markup uses no --papel-*/--s-* tokens), so the CSS-boundary rules are not in play for this round's change. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q` for the Python side; `npx vitest run` and `npx astro check` for the web side; plus `uv run okf-parser check knowledge --relational-schema okf.schema.sql` and `uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs` for the OKF report."
---

# Leitura de CLAUDE.md

Dois runtimes: `djen-backup` (Python) e `web/` (Astro+Svelte). Nenhuma regra de correção do `djen-backup` é relevante para o trabalho desta rodada. A fronteira `### CSS token boundary`, corrigida pela rodada anterior (`ttdopu`, PR #1185), permanece correta e verificada ao vivo — mas não é relevante para o componente tocado nesta rodada (`DuckDBExplorer.svelte` não usa tokens legados `--papel-*`/`--s-*`). Gates a rodar antes de commitar: `ruff check`/`ruff format --check`/`pytest -q` (Python) e `vitest run`/`astro check` (web), além do `okf-parser check` e do checker de completude dos relatórios.

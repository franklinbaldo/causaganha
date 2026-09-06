---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-3kjpfr-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md (full file, this session's system context)"
finding: "Repo has two runtime surfaces (Python backend src/causaganha + src/djen_backup; web/ Astro 5 + Svelte 5). This round's chosen work (issue #1131, /stats drill-down over tribunal_calendar) lives entirely in web/src/lib and web/src/components/pages — none of the djen_backup correctness rules (sync-manifest.parquet source of truth, djen_raw vs djen_status, 403≠absent, per-item IA locks) apply since no Python file changes. The CSS token boundary section documents the current reality accurately (single Panda CSS design system via the cobogo preset; web/src/index.css is a compatibility-alias bridge for exactly four named legacy Svelte islands: ProcessoLookup, PublicationSearch, SavedConsultations, TribunalCalendar). The new component this round adds (a tribunal/period drill-down for /stats) is NOT one of those four legacy islands, so it must be styled with Panda css()/recipes from the start, never new bespoke --custom-properties. 'Before committing' gate (ruff check, ruff format --check, pytest -q) still applies even for a web-only change to confirm no accidental Python regression."
---

# Leitura de CLAUDE.md

Confirma que nenhuma regra de negócio de `djen_backup` se aplica ao trabalho desta rodada (issue #1131, inteiramente em `web/`), e que o novo componente desta rodada deve usar Panda CSS (`css()`/recipes), não os aliases legados de `index.css` — que estão reservados às quatro ilhas Svelte já nomeadas (nenhuma delas é o componente novo desta rodada).

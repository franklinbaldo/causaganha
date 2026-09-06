---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-tp38w3-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md (full file, this session's system context)"
finding: "Repo has two runtime surfaces (Python backend src/causaganha + src/djen_backup; web/ Astro 5 + Svelte 5). The djen_backup-specific correctness rules (sync-manifest.parquet as source of truth, djen_raw vs djen_status, 403≠absent, upload-bug read_bytes(), per-item IA locks) belong to the DJEN sync-manifest domain and do not apply to this round's chosen work, which lives entirely in web/src/lib and web/src/components (saved-consultation change tracking, issue #1133). The CSS token boundary section already documents the current single-Panda-preset reality (a prior round, 2026-09-06-exciting-mccarthy-ttdopu, fixed this after four earlier rounds flagged it stale) — SavedConsultations.svelte is one of the four named legacy Svelte islands still using --papel-*/--s-* aliases, so this round's UI edit correctly kept using those existing aliases rather than introducing new bespoke custom properties or converting the whole component to Panda css(), per the explicit 'maintaining one of the four legacy islands' guidance. Style rules that do apply: ruff strict/no blind except Exception for any Python touched (this round touched none); 'Before committing' gate (ruff check, ruff format --check, pytest -q) verified green even though no Python files changed, confirming no accidental Python regression from a web-only change."
---

# Leitura de CLAUDE.md

Confirma que as regras de negócio de `djen_backup` (sync-manifest, djen_raw/djen_status) não se aplicam ao trabalho desta rodada (issue #1133, inteiramente em `web/`). Confirma também que `SavedConsultations.svelte` é um dos quatro componentes Svelte legados listados na seção "CSS token boundary" — a rodada manteve o vocabulário `--papel-*`/`--s-*` já existente ali, sem introduzir novas custom properties, conforme a orientação explícita do arquivo.

---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-ich5gz-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md (full file, this session's system context)"
finding: "Repo has two runtime surfaces (Python backend src/causaganha + src/djen_backup; web/ Astro 5 + Svelte 5). Manifest query contracts: web declares data needs via .qmd files rendered by scripts/render_queries.py into web/public/data/. Correctness rules for djen_backup (403≠absent, 200-without-URL=absent, djen_raw is transport code not verdict) are specific to the sync-manifest domain, not the processo-consulta domain this round works in. Style: ruff strict (no blind except Exception, TRY300/301/401 enforced), Python 3.12+ with | unions and `from __future__ import annotations`. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Web tests run via `cd web && npm test`/vitest (not explicitly in CLAUDE.md but established by prior rounds' evidence). None of CLAUDE.md's explicit 'What NOT to do' items (boto3, per-item lock removal, mark_djen_raw with derived category, non-.qmd cache generation, broad except Exception) are touched by this round's chosen work (issue #1107, processo query-plan parity), which lives entirely in src/causaganha/processos/ and web/src/lib/processoCnj.ts + its parity test harness."
---

# Leitura de CLAUDE.md

Confirma que as regras de negócio específicas de djen_backup (sync-manifest, djen_raw/djen_status, uploads IA) não se aplicam ao trabalho desta rodada (contrato processo/#1107); as regras de estilo (ruff estrito, sem `except Exception` genérico, checks antes de commit) sim se aplicam e serão seguidas.

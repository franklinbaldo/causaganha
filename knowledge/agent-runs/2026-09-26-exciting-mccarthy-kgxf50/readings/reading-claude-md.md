---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-kgxf50-reading-claude-md"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces (djen-backup sync engine + web/ Astro/Svelte dashboard); manifest.parquet is the single source of truth for djen-backup, not directly relevant to this round's chosen work. Rules of the road that DO apply: ruff strict/no blind except Exception, TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`. Manifest query contracts (.qmd -> Zod schema in web/src/lib/data/contracts.ts) unrelated to segmenter work this round."
---

# Reading: CLAUDE.md

Confirmed full read of `/home/user/causaganha/CLAUDE.md` at session start.
Key points that constrain this round's work (segmenter dataset, per the
handoff in `next_move` of the prior round):

- Style rules apply repo-wide regardless of subsystem: ruff strict, no
  blind `except Exception` (specific types or the per-item bulkhead ADR
  0011 pattern), TRY300/TRY301/TRY401 enforced, Python 3.12+ with
  `from __future__ import annotations` at the top of new modules.
- "Before committing" gate: `uv run ruff check`, `uv run ruff format
  --check`, `uv run pytest -q` — all three must be run before any push.
- The djen-backup/manifest and web CSS-token sections describe a
  different subsystem (DJEN sync engine, Panda CSS frontend) that this
  round's selected work (segmenter dataset annotation, `src/segmenter_dataset`
  + `scripts/*segmenter*`) does not touch — noted as read, not as a
  constraint on this round's diff.
- No repo-specific OKF/scaffold instructions live in CLAUDE.md itself;
  those come from `.claude/agent-run-scaffold.md`, read separately.

---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-sg2540-reading-claude-md"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces (djen-backup sync engine + web/ Astro/Svelte dashboard); manifest.parquet correctness rules and the CSS token boundary are the repo's two most detailed sections but neither applies to this round's chosen work (segmenter dataset annotation lives in src/segmenter_dataset + scripts/*segmenter*, touching neither djen-backup nor web/). Repo-wide rules that DO apply: ruff strict (no blind except Exception; TRY300/301/401 enforced), Python 3.12+ with `from __future__ import annotations`, and the 'Before committing' gate (ruff check, ruff format --check, pytest -q)."
---

# Reading: CLAUDE.md

Confirmed full read of `/home/user/causaganha/CLAUDE.md` at session start.

- The djen-backup section (sync-manifest.parquet as single source of
  truth, `djen_raw` vs `djen_status` semantics, 403-is-not-absent rule)
  and the CSS token boundary section describe subsystems this round's
  selected work does not touch. Noted as read, not as a constraint on
  this round's diff.
- Style rules apply repo-wide: ruff strict, no blind `except Exception`,
  TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__
  import annotations` at the top of new modules.
- "Before committing" gate: `uv run ruff check`, `uv run ruff format
  --check`, `uv run pytest -q` -- all three run before any push this round.
- CLAUDE.md carries no OKF/scaffold instructions; those live in
  `.claude/agent-run-scaffold.md`, read separately.

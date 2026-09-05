---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-sf5rj3-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-sf5rj3"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup (src/djen_backup) with sync-manifest.parquet on IA as sole canonical source, and the web frontend (Astro 5 + Svelte 5) fed by .qmd query contracts. Style rules relevant to any Python change this round: Ruff is strict (no blind `except Exception`, TRY300/TRY301/TRY401 enforced, specific exception types only), Python 3.12+ with `|` unions and `from __future__ import annotations`. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. This round's selected work (verifying and closing issue #1052, a segmenter evaluation-harness issue) touches neither djen-backup nor the web frontend and requires zero source changes, so none of the manifest/DJEN-status invariants or the CSS token boundary are exercised; the ruff/pytest gates are still run in full as evidence that the repository stays green."
---

# Leitura de CLAUDE.md

Regras de estilo Python (ruff estrito) e a separação djen-backup/web confirmadas; nenhuma é tocada pelo trabalho desta rodada, que é uma verificação de estado de uma issue do segmenter sem mudança de código.

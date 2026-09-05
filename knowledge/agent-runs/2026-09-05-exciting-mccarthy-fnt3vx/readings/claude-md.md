---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-fnt3vx-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup (src/djen_backup) with sync-manifest.parquet on IA as sole canonical source, and the web frontend (Astro 5 + Svelte 5) fed by .qmd query contracts. Style rules relevant to any Python change this round: Ruff is strict (no blind `except Exception`, TRY300/TRY301/TRY401 enforced, specific exception types only), Python 3.12+ with `|` unions and `from __future__ import annotations`. 'What NOT to do' explicitly forbids boto3 for IA uploads and removing the per-item lock in archive.py — neither is touched this round. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. No djen-backup or web frontend behavior is planned to change this round (the selected work is Python-side test/dataset-tooling hygiene), so the manifest/DJEN-status invariants and CSS token boundary are read for completeness but are not directly exercised."
---

# Leitura de CLAUDE.md

Confirma as regras de estilo Python (ruff estrito, sem `except Exception` cego, gates de pre-commit) e a separação de superfícies (djen-backup vs. web). Nenhuma delas é violada nem diretamente tocada pelo trabalho escolhido nesta rodada (limpeza de módulos órfãos em `experiments/archive/` e fechamento de checklist da issue #1048 do segmenter).

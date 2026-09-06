---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-usm2ot-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (src/djen_backup, manifest.parquet as sole source of truth since Fase 3 of docs/planning/manifest-source-of-truth.md) and web/ (Astro 5 + Svelte 5) fed by .qmd query contracts. This round's selected work (a durable 'blocked backlog' registry under knowledge/backlog/, new BacklogItem OKF type) touches neither djen_backup nor web/ production code — no djen_raw/djen_status logic, no CSS token boundary, no query contract. 'Before committing' gates (ruff check/format, pytest -q) still apply because new Python tests are added under tests/knowledge/, and the round's own OKF report lives under knowledge/agent-runs/, validated by scripts/check_agent_run_completeness.py and okf-parser check."
---

# Leitura de CLAUDE.md

Dois runtimes documentados (djen-backup e web/), nenhum tocado por esta rodada. O trabalho fica em `knowledge/` (novo type `BacklogItem` + registro de 17 issues) e em um teste Python novo que valida esse registro — por isso os gates `ruff check`/`ruff format --check`/`pytest -q` seguem valendo, mas nenhuma regra específica de djen_raw/CSS se aplica.

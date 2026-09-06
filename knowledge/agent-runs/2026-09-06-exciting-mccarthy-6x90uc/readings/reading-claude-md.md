---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-6x90uc-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces (djen-backup sync engine in src/djen_backup, and web/ Astro+Svelte fed by .qmd query contracts). Neither is touched this round: the selected work is scripts/check_agent_run_completeness.py, this project's own OKF round-report tooling, not documented in CLAUDE.md itself but governed by its 'Style' section — Python 3.12+, `from __future__ import annotations`, ruff strict with no blind `except Exception` (BLE001), TRY300/TRY301/TRY401 enforced. Gates before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Since no djen_backup or web file changes, the djen_raw/djen_status correctness rules and the CSS token boundary section are both out of scope this round."
---

# Leitura de CLAUDE.md

Dois runtimes documentados (djen-backup e web/); nenhum é tocado nesta rodada. O trabalho fica em `scripts/check_agent_run_completeness.py`, coberto pela seção "Style" (Python 3.12+, `from __future__ import annotations`, ruff estrito, sem `except Exception` genérico). Gates: `ruff check` / `ruff format --check` / `pytest -q`.

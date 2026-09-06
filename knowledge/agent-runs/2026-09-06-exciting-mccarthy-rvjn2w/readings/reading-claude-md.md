---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-rvjn2w-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-rvjn2w"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces documented (djen-backup sync engine, web/ Astro+Svelte). This round's selected work sits entirely in the MCP product surface (src/causaganha_mcp/tools/decisoes.py and src/causaganha/decisoes/{published,planner,search}.py) and touches neither djen_backup's manifest/DJEN-status rules nor any .qmd query contract nor the web/ CSS token boundary, so those sections do not constrain this round. The applicable rules are the general Python ones: Ruff is strict (no blind except Exception; use specific types — the existing code already narrows to duckdb.Error/httpx.HTTPError-style exceptions, a pattern to keep); TRY300/TRY301/TRY401 enforced; Python 3.12+ with `from __future__ import annotations`. 'Before committing' gates apply: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`."
---

# Leitura de CLAUDE.md

Trabalho desta rodada é puramente Python/MCP (`src/causaganha_mcp/tools/decisoes.py` + `src/causaganha/decisoes/published.py`), não toca `djen_backup`, `.qmd` nem `web/`. Regras relevantes: Ruff estrito (sem `except Exception` genérico, TRY300/301/401), Python 3.12+ com `from __future__ import annotations`. Gates: `ruff check`, `ruff format --check`, `pytest -q`.

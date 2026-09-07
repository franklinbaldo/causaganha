---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-kfv7sx-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-kfv7sx"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "This round's selected work (issue #1244, splitting the MCP tool catalog into an explicit public/operator composition) is pure src/causaganha_mcp code plus its pytest contract tests — it touches neither djen_backup's manifest/DJEN-status correctness rules nor any .qmd query contract nor the web CSS token boundary (the only web-side change is switching an existing contract test, test_web_agents_contract.py, from build_server() to build_public_server() — no .astro/.svelte production file changes). The relevant CLAUDE.md rules are the generic Python ones: ruff is strict (no blind except Exception; specific httpx/OSError/RuntimeError types), TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__ import annotations`. 'Before committing' gates apply: ruff check, ruff format --check, pytest -q."
---

# Leitura de CLAUDE.md

Trabalho desta rodada é código MCP puro (`src/causaganha_mcp/`) mais testes de contrato Python — não toca `djen_backup`, contratos `.qmd` nem a fronteira de tokens CSS (a única mudança do lado web é um teste de contrato trocando `build_server()` por `build_public_server()`, sem alterar `.astro`/`.svelte` de produção). Regras relevantes: ruff estrito, sem `except Exception` genérico, TRY300/TRY301/TRY401, `from __future__ import annotations`. Gates: `ruff check`, `ruff format --check`, `pytest -q`.

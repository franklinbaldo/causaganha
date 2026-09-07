---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-abz39i-reading-claude-md"
run_id: "2026-09-07-exciting-mccarthy-abz39i"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md, full file, read at session start"
finding: "The 'Before committing' checklist (uv run ruff check; uv run ruff format --check; uv run pytest -q) is the exact gate this round's work must clear before any push, and 'No blind except Exception' / TRY300/TRY301/TRY401 are the style constraints that apply to any causaganha_mcp code touched. CLAUDE.md has no section specific to src/causaganha_mcp (its architecture section covers djen-backup and the web query-contract pipeline only), so MCP-catalog work is governed by the generic Python style rules plus whatever tests already encode the intended MCP behavior — consistent with prior rounds (kfv7sx) treating tests/causaganha_mcp/*.py as the actual contract for this subsystem."
---

# Leitura de CLAUDE.md

Nenhuma seção específica sobre `causaganha_mcp`; regras aplicáveis a este round são as gerais de estilo Python (ruff estrito, sem `except Exception` genérico) e o checklist "Before committing", usado como gate antes de qualquer push.

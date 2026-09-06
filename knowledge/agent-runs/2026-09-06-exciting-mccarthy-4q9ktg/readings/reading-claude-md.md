---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-4q9ktg-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-4q9ktg"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces (djen_backup sync engine in src/djen_backup, web/ Astro+Svelte frontend), plus src/causaganha_mcp as the MCP tool surface that recent rounds have been extending. This round's own network probe reproduced CLAUDE.md's documented djen_raw/djen_status distinction is already correctly implemented in src/djen_backup/djen.py (get_caderno_url treats 404/400 as absent, 403 as DJENRateLimitedError — never absent — and a 200-with-'Sem comunicações' body as absent via DJENNotFoundError(status_code=200), matching the doc's availability rule exactly). No djen_backup or .qmd-contract work was selected this round (see goal), so the manifest/DJEN correctness rules and the CSS token boundary rules were read for situational awareness but did not gate an implementation choice. 'Before committing' gates (ruff check, ruff format --check, pytest -q; npm run lint/typecheck/test for web/) were run directly this round as part of establishing a clean baseline before searching for work, independent of any specific change."
---

# Leitura de CLAUDE.md

Dois runtimes (djen_backup, web/) mais o MCP tool surface (`src/causaganha_mcp`), que tem sido o alvo mais ativo das últimas ~19 rodadas de hoje. Verifiquei ao vivo que a distinção `djen_raw`/`djen_status` documentada está corretamente implementada em `src/djen_backup/djen.py::get_caderno_url` (404/400 = ausente, 403 = `DJENRateLimitedError` nunca ausente, 200 com `"Sem comunicações"` = ausente via `DJENNotFoundError(status_code=200)`). Rodei os gates de "Before committing" (`ruff check`, `ruff format --check`, `pytest -q`, `npm run lint`/`typecheck`/`test`) como parte do baseline desta rodada, antes de escolher o trabalho.

---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-9xpeua-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "djen-backup's sync-manifest.parquet on IA is the sole canonical source of DJEN sync state; djen_raw is the raw HTTP status only, never a verdict (200-with-no-download-URL is genuinely absent, same as 404/400; 403 must never be treated as absent). The frontend (web/src/queries/*.qmd -> scripts/render_queries.py -> web/public/data/*.json) and the /processo dossier (web/src/lib/processoCnj.ts, buscarProcesso) are the two runtime surfaces most active in the open backlog right now (contract(processo) issue #1107, web/proveniencia issue #1135). Ruff is strict (no blind except Exception, TRY300/301/401 enforced); pre-commit gate is ruff check, ruff format --check, pytest -q. This CLAUDE.md has no explicit web/ frontend test-gate command, so web changes are verified with `cd web && npx vitest run` plus the existing `npm run lint`/`typecheck` scripts."
---

# Leitura de CLAUDE.md

Confirma as invariantes do pipeline djen-backup (não centrais a esta rodada, que trabalha no frontend) e localiza onde o contrato de dados do site vive: `.qmd` -> `contracts.ts` para dados agregados, e `web/src/lib/processoCnj.ts` para o dossiê client-side por CNJ, que é a superfície tocada nesta rodada.

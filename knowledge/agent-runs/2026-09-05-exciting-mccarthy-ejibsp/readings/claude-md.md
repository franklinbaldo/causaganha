---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-ejibsp-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "djen-backup's sync-manifest.parquet on IA is the sole canonical source (sync-manifest.csv is a retired derived export); djen_raw is the raw DJEN HTTP status, never a verdict on availability — a 200 with body \"Sem comunicações\" (no download URL) is genuinely absent, same as 404/400, and 403 must never be treated as absent (CloudFront/WAF rate-limit); the frontend declares data needs via .qmd query contracts under web/src/queries/ rendered by scripts/render_queries.py, plus Zod schemas in web/src/lib/data/contracts.ts; ruff is strict (no blind except Exception, TRY300/301/401 enforced); pre-commit gate is ruff check, ruff format --check, pytest -q."
---

# Leitura de CLAUDE.md

Confirma as invariantes de correção do pipeline DJEN e as regras de estilo/lint, e situa que este bundle OKF (`knowledge/`) é uma camada separada — descreve conhecimento e contratos do produto, não os dados arquivados em si (Parquet/DuckDB continuam sendo o plano de dados).

---
type: AgentReading
id: "2026-09-05-eager-wozniak-5akx2o-reading-claude-md"
run_id: "2026-09-05-eager-wozniak-5akx2o"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "djen-backup's sync-manifest.parquet is the sole canonical source (sync-manifest.csv is a retired derived export); djen_raw is the raw HTTP status, never a verdict — availability requires HTTP 200 AND a download URL in the body; 403 must never be treated as absent; the web frontend consumes JSON via .qmd query contracts, not ad-hoc scripts; ruff is strict (no blind except Exception, TRY300/301/401 enforced); commands to run before committing are ruff check, ruff format --check and pytest."
---

# Leitura de CLAUDE.md

Confirma as invariantes de correção (403 != absent, 200 sem URL == absent, sync-manifest.parquet como fonte única) e as regras de estilo/lint que qualquer avanço desta rodada precisa respeitar.

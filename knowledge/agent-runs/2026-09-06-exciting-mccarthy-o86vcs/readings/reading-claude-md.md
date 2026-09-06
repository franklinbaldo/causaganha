---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-o86vcs-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-o86vcs"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md as checked out at commit ac7f7f9 (origin/main)"
finding: "Architecture: djen-backup sync engine treats sync-manifest.parquet on IA as sole source of truth; djen_raw is a transport code, not a verdict — availability requires HTTP 200 AND a download URL in the body, never a bare 200. Frontend declares data needs via .qmd query contracts rendered to web/public/data/ JSON by scripts/render_queries.py. CSS token boundary: single Panda CSS design system via the cobogo preset covers all substantive pages; web/src/index.css is a compatibility bridge consumed only by four legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations, TribunalCalendar) because panda.config.ts's include never scans .svelte files. No stale-documentation drift found in this reading (a prior round, ttdopu, already rewrote this section from the retired Pico/Brazilian-Modernism model). Rules of the road: never treat 403 as absent; specific exception types only (no blind except Exception, BLE001-enforced); TRY300/301/401 enforced; ia_s3._perform_upload must use read_bytes(), not open('rb'). Before-committing gate is ruff check/format + pytest -q; web has its own gate (npm run lint/typecheck/test/build, wired into .github/workflows/test.yml's web job since round m65xwe)."
---

# Leitura de CLAUDE.md

CLAUDE.md está atualizado e não aponta nenhuma lacuna de documentação nesta rodada — a seção de fronteira CSS (historicamente instável) já reflete a arquitetura Cobogó/Panda atual. As regras de correção sobre `djen_raw`/`djen_status` e a política de exceções específicas (sem `except Exception`) seguem valendo como restrições de qualquer mudança desta rodada.

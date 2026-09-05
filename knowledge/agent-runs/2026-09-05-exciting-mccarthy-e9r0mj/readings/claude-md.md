---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-e9r0mj-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: Python djen-backup sync engine (src/djen_backup, sync-manifest.parquet as sole canonical source) and the web frontend (Astro 5 + Svelte 5) under web/. This round's candidate work (issue #1107, DataJud temporal-authority drift) touches neither djen_raw/djen_status semantics nor .qmd query contracts — it is a bug in the /processo dossier mapping layer (web/src/lib/processoCnj.ts's mapDatajudRow) plus its Python counterpart's parity harness (src/causaganha/processos/service.py, query_plan_fixtures.py). CLAUDE.md's 'Rules of the road' on correctness (never silently normalize away a discrepancy you find, verify against the real source before trusting a recorded value) and its Python style rules (Ruff strict, no blind except Exception, TRY300/301/401) apply to any Python-side change; the CSS token boundary does not apply since no styling changes. Before-committing gate: uv run ruff check / ruff format --check / pytest -q for Python; cd web && npx vitest run / npm run lint / npm run typecheck for Web, since this round's change spans both runtimes (Python _iso() vs Web toIsoDate())."
---

# Leitura de CLAUDE.md

Confirma que a mudança candidata (drift de timestamp DataJud entre Python e Web, issue #1107) é um bug de camada de mapeamento em ambos os runtimes, não toca o pipeline djen-backup nem contratos `.qmd`, e deve passar pelos gates de qualidade dos dois lados (ruff/pytest e vitest/eslint/typecheck) por tocar Python e TypeScript na mesma rodada.

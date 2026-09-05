---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-1fxd8b-reading-claude-md"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: Python djen-backup sync engine (src/djen_backup) with sync-manifest.parquet on IA as sole canonical source, and the web frontend (Astro 5 + Svelte 5) under web/ whose aggregate data comes from .qmd query contracts rendered by scripts/render_queries.py. This round's candidate work (issue #1130, evidence-matrix strip on /processo) touches only the web surface and reuses an existing per-source dossier contract rather than any .qmd/manifest data, so djen_raw/djen_status semantics and IA upload invariants are not in scope. The binding constraint for this round is the CSS token boundary: /processo is a container-layout data page, so any new component must use semantic tokens (--color-*, --space-*, --pico-*) and must NOT use Brazilian Modernism tokens (--s-*, --papel-*, --tinta-*), which are reserved for the homepage/marketing surfaces. Pre-commit gates for a web-only change: cd web && npx vitest run, npm run lint, npm run typecheck (baseline has pre-existing errors from earlier rounds' reports, must diff before/after); Python gates (ruff check, ruff format --check, pytest -q) apply only if Python files are touched."
---

# Leitura de CLAUDE.md

Confirma que a mudança candidata desta rodada (issue #1130) fica inteiramente na superfície web, não toca o pipeline djen-backup nem contratos .qmd, e deve respeitar a fronteira de tokens CSS semânticos (não Brazilian Modernism) por ser uma página de dados com layout `container`.

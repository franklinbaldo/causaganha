---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-b0lycs-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-b0lycs"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (src/djen_backup) and web/ (Astro 5 + Svelte 5) fed by .qmd query contracts under web/src/queries/, rendered by scripts/render_queries.py into web/public/data/*.json and loaded via loadContract()/web/src/lib/data. The CSS token boundary section (rewritten last round, PR #1185) now correctly describes a single Panda CSS design system via the `cobogo` preset, with web/src/index.css as a compatibility bridge for four named legacy Svelte islands — verified still accurate this round, no drift found. None of the djen-backup correctness rules (djen_raw vs djen_status, 403≠absent, per-item IA lock) are implicated by this round's candidate work, which is entirely inside web/. Relevant rule for this round: 'Don't generate cache JSONs from random sources. Canonical source is the manifest; use .qmd query contracts' — read as: any per-tribunal partitioning of tribunal_calendar must still derive from the same canonical contract, not a second source of truth. Before committing: uv run ruff check / ruff format --check / pytest -q (repo-wide gate, even for a web/-only change, per 'Before committing' section), plus the web/-specific gates (npm run lint, npm test, npm run build) which CLAUDE.md's file map implies but doesn't spell out — confirmed from web/package.json scripts and .github/workflows/test.yml's web job."
---

# Leitura de CLAUDE.md

Dois runtime surfaces (djen-backup e web/), contrato `.qmd` → JSON como fonte única de verdade para o frontend. A seção CSS (corrigida na rodada anterior, PR #1185) segue correta — sem deriva encontrada. Nenhuma regra de correção do djen-backup é relevante para o trabalho desta rodada, que é inteiramente em `web/`. Regra aplicável: não criar uma segunda fonte de verdade para dados já cobertos por um contrato `.qmd` — qualquer particionamento de `tribunal_calendar` deve derivar do mesmo contrato canônico.

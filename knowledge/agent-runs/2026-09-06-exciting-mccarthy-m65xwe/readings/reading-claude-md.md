---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-m65xwe-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: djen-backup sync engine (src/djen_backup) and web/ (Astro 5 + Svelte 5) fed by .qmd query contracts rendered to web/public/data/*.json. This round's selected work touches only web/ test files (three ProcessoLookup.*.test.ts files, one shared Svelte-testing-library render wrapper, one integration test) plus .github/workflows/test.yml — no djen_backup, no production Svelte/Astro component, no query contract. The 'CSS token boundary' and 'djen_raw/djen_status correctness' rules are out of scope: no styling or manifest-reading code is touched. 'Before committing' gates (ruff check/format, pytest -q) still apply because the round's own OKF report lives under knowledge/agent-runs/, validated by scripts/check_agent_run_completeness.py and okf-parser."
---

# Leitura de CLAUDE.md

Dois runtimes documentados (djen-backup e web/). O trabalho desta rodada fica inteiramente em `web/` (arquivos de teste + wrapper de teste + workflow de CI), sem tocar componentes de produção, manifesto DJEN ou contratos `.qmd`. As seções de correção de `djen_raw`/CSS token boundary não se aplicam. Os gates Python (`ruff check`, `ruff format --check`, `pytest -q`) seguem valendo por causa do próprio relatório OKF desta rodada.

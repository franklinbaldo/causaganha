---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-71376p-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-71376p"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Repo guide confirms the djen-backup sync engine (single source of truth = sync-manifest.parquet on IA), the manifest query contract flow (.qmd -> render_queries.py -> web/public/data/), the Panda/Cobogo CSS token boundary (three legacy Svelte islands keep --papel-*/--s-* names), and the strict ruff/TDD/no-broad-except style rules. None of this changed since the last reading in this lineage; no new correctness gotcha directly touches this round's work (a merge-conflict reconciliation in the #1050 segmenter corpus lineage, prose/test files only)."
---

# Leitura: CLAUDE.md

Reconfirmação de leitura obrigatória do `AgentRun` desta rodada. Nada
mudou de relevante em relação às leituras anteriores da mesma linhagem
(zrek2s, imy2ed, hv2ep2): as regras de correção do `djen_raw`/`djen_status`,
o contrato de queries `.qmd`, a fronteira Panda/legacy CSS e as regras de
estilo (ruff estrito, TRY300/301/401, `from __future__ import annotations`)
seguem valendo e não intersectam o trabalho desta rodada.

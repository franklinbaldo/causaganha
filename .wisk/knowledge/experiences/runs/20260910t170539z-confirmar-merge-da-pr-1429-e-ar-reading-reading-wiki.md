---
type: "RunReading"
id: "run-readings/20260910t170539z-confirmar-merge-da-pr-1429-e-ar/reading-wiki"
run: "runs/20260910T170539Z-confirmar-merge-da-pr-1429-e-arquivar-o-handoff"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants.md's except-Exception scoped-audit lineage (paragraph 59 and its PR #1427 continuation)"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "The lineage's PR #1427 entry left 12 sites across 5 scripts/ files: batch_embed_decisions.py (3), build_gold_benchmark.py (1), daily_benchmark_update.py (1) already noqa'd; dev/cleanup_deprecated_ia_items.py (3) and generate_catalog.py (4) still needing the full per-site read. This round's PR #1429 closes the latter two: cleanup_deprecated_ia_items.py's 2 per-item bulkheads cited, 1 single-shot search narrowed; generate_catalog.py's all 4 single-shot DuckDB/metrics sites narrowed. 3 sites now remain, all already noqa'd -- a lighter confirm-and-cite pass rather than a fresh read."
---

# RunReading

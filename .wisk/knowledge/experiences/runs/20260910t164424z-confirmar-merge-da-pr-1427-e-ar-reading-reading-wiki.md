---
type: "RunReading"
id: "run-readings/20260910t164424z-confirmar-merge-da-pr-1427-e-ar/reading-wiki"
run: "runs/20260910T164424Z-confirmar-merge-da-pr-1427-e-arquivar-o-handoff"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants.md paragraph 59 (except-Exception scoped-audit lineage)"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "Paragraph 59 traces the lineage through PR #1425: two scripts/ files narrowed/cited, leaving 22 sites across 6 files (batch_embed_decisions.py, build_gold_benchmark.py, daily_benchmark_update.py already noqa'd; dev/cleanup_deprecated_ia_items.py, generate_catalog.py, pipeline/consolidate.py -- the largest at 10 sites -- still needing the full per-site read). This round's PR #1427 closes the consolidate.py branch of that lineage: 6 of its 10 sites cited (matching src/causaganha/consolidate/cli.py:172's own pre-existing per-table bulkhead, the ADR's own example), 4 narrowed. 12 sites now remain across 5 files (batch_embed_decisions.py, build_gold_benchmark.py, daily_benchmark_update.py, dev/cleanup_deprecated_ia_items.py, generate_catalog.py)."
---

# RunReading

---
type: "RunReading"
id: "run-readings/20260910t114603z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260910T114603Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "Read the full lineage of 23 numbered root-cause-family paragraphs plus the running PR/handoff log through PR #1417/#1418. This round's fix is closest to pattern eighteen (a migration -- the djen-{tribunal}-{year} consolidated-parquet layout replacing per-day items -- leaves a stale assumption behind, here a SQL filter written against the old date-per-file column) and pattern fourteen (an invariant assumed true everywhere a value is consumed, when a producer's own carve-out makes it false on a real path) -- but distinct from both: neither is about a *query filter* silently excluding valid current-schema rows because it was written before the schema's own most recent evolution."
---

# RunReading

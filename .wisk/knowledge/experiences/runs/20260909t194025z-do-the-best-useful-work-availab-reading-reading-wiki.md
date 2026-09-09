---
type: "RunReading"
id: "run-readings/20260909t194025z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260909T194025Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "14 prior patterns recorded, spanning duplicated-classification-logic drift, doc-drift, dead-code-with-real-bug, hardcoded-no-op gates, and the fresh-checkout wisk init . gotcha. This round's own fix (render_queries.py's per-contract try/except catching only duckdb.CatalogException, missing the sibling ValueError/duckdb.Error a broken contract's own query raises) is a distinct root-cause family not yet named: an error-isolation boundary meant to contain one failing unit of a batch was scoped to only one exception type from that unit's call, so a different exception type from the same call silently escapes containment and takes the whole batch down. Worth recording as a 15th pattern."
---

# RunReading

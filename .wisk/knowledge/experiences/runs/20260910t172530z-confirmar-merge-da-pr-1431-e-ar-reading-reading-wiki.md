---
type: "RunReading"
id: "run-readings/20260910t172530z-confirmar-merge-da-pr-1431-e-ar/reading-wiki"
run: "runs/20260910T172530Z-confirmar-merge-da-pr-1431-e-arquivar-o-handoff"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants.md's except-Exception scoped-audit lineage (its full arc from paragraph 41 through the PR #1429 continuation)"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "The lineage's PR #1429 entry left 3 sites remaining, all already noqa'd. This round's PR #1431 closed all 3: batch_embed_decisions.py's 3 sites were found NOT to be bulkheads on direct verification (contradicting the framing carried forward since PR #1425) and narrowed to google.genai.errors.APIError; build_gold_benchmark.py/daily_benchmark_update.py's 1 site each are genuine bulkheads but lacked real traceback capture, so console.print_exception() was added alongside the ADR citation. A repo-wide grep now confirms zero uncited/unnarrowed bare except-Exception remains in src/ or scripts/ -- the lineage started by PR #1289 is fully closed."
---

# RunReading

---
type: "RunReading"
id: "run-readings/20260910t134021z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260910T134021Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "Read the full lineage through PR #1421/#1422 (twenty-seventh pattern: generate_homepage_widgets.py's year-boundary rolling-window gap). This round's fix (PR #1423) is a distinct pattern from that lineage -- not a rolling-window bug, but an instance of the existing 'shared domain exception/policy needs auditing against every call site' family (already documented here for DJENRateLimitedError and the absent-self-consistency rule): docs/adr/0011's bulkhead citation requirement was enforced only against src/ by tests/test_except_exception_policy.py, so a structurally-identical bulkhead in scripts/ went unaudited until this round's targeted grep found it."
---

# RunReading

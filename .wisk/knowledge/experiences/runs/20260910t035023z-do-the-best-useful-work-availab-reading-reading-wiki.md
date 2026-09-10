---
type: "RunReading"
id: "run-readings/20260910t035023z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260910T035023Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: "Existing WikiEntry, 18 pattern paragraphs, most recently the note that PRs #1395/#1397 landed via the deprecated knowledge/agent-runs/ AgentRun mechanism because a separate scheduled session's literal prompt still pointed at that legacy scaffold."
finding: "No paragraph yet names the specific bug family PR #1403 fixed: a documented CLI-mode I/O contract (SyncConfig.check_only, fixed by #1397) gets audited and fixed, but a sibling boolean flag on the exact same dataclass, gating the exact same run_pipeline code path for an analogous documented contract (SyncConfig.upload_only), is never checked for the identical unenforced-flag bug -- until a later round (this one) greps the sibling explicitly. This is a same-file/same-function variant of the broader 'a fix to one consumer of a shared concept does not propagate to a sibling consumer' family already named for .qmd contracts (16th pattern) and exception-handling call sites, but distinct enough (config-flag siblings inside one dataclass/function, not separate files) to be worth its own bullet plus a concrete generalizable check: when a boolean config field's documented contract is found unenforced and fixed, grep every other boolean field on the same config dataclass for the same 'set but never read, or read in only one of several places it should gate' shape before closing the round."
---

# RunReading

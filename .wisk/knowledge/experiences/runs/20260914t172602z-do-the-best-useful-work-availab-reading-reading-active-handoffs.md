---
type: "RunReading"
id: "run-readings/20260914t172602z-do-the-best-useful-work-availab/reading-active-handoffs"
run: "runs/20260914T172602Z-do-the-best-useful-work-available-in-this-reposi"
kind: "active-handoffs"
subject: "Active handoffs relevant to this round"
reference: "wisk start (selection_reason=handoff-continuation) + Read of handoffs/handoff-issue-1471-perf-and-readback"
finding: "One active handoff: handoffs/handoff-issue-1471-perf-and-readback, created by runs/20260914T152436Z, superseding handoffs/handoff-issue-1471-pilot-validation. Its baseline (repository_head=729e9c08d, dirty=true) is a phantom commit that does not exist in real git history -- the creating round's own uncommitted local state was lost when its ephemeral container was reclaimed, consistent with repository_dirty=true never having been committed. next_action: (1) measure DuckDB native+WASM date-only query cost under the new numero_processo-first ordering vs the currently published file, separating engine init/cold query/warm cache, recording bytes/requests/duration/sample/environment; (2) publish the candidate to djen-tjro-2026 on Internet Archive preserving rollback, then a controlled read-back proof distinguishing real Archive delivery from local simulation; (3) only then record the issue #1471 advance/revise/hold decision. Confirmed via GitHub reads: issue #1471 still open, PR #1478 (the local-validation slice) merged (65e0653), PR #1479 recorded that merge in the wiki -- no other PR open against #1471."
---

# RunReading

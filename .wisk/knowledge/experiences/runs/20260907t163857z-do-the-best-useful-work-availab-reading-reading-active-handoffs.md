---
type: "RunReading"
id: "run-readings/20260907t163857z-do-the-best-useful-work-availab/reading-active-handoffs"
run: "runs/20260907T163857Z-do-the-best-useful-work-available-in-this-reposi"
kind: "active-handoffs"
subject: "Active handoffs at run start"
reference: "handoffs/handoff-pr-1277-awaiting-ci"
finding: "wisk start selected this run via handoff-continuation on handoffs/handoff-pr-1277-awaiting-ci. PR #1282 (opened by an independent concurrent session) was meant to resolve it but had sat open for about an hour: created 15:32Z against a now-stale main base (335fb89) while main had advanced to ba08073, mergeable_state=behind, and merge_pull_request returned an HTTP 405 requiring a GitGuardian status check absent from the head SHA. After update_pull_request_branch and a fresh green check run, the squash merge succeeded (a7e0d7d) and the handoff is now archived on main; git fetch confirms 0 active handoffs remain."
---

# RunReading

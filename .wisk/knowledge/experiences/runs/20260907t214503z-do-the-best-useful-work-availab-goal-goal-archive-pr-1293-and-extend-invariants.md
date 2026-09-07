---
type: "RunGoal"
id: "run-goals/20260907t214503z-do-the-best-useful-work-availab/goal-archive-pr-1293-and-extend-invariants"
run: "runs/20260907T214503Z-do-the-best-useful-work-available-in-this-reposi"
kind: "consolidate-knowledge"
goal: "Confirm PR #1293 is merged into main, archive handoffs/handoff-pr-1293-awaiting-ci, and extend wiki/continuous-loop-operational-invariants.md with this round's grounded finding: circuit_breaker.py's sync/async split (ia_s3.py's sync-only is_open+record_failure path vs. archive.py/engine.py/drain.py's async allow_request path) has now produced three same-day bugs, all found by reading the module against its real callers rather than in isolation."
rationale: "handoff-pr-1293-awaiting-ci's remaining obligation (merge PR #1293, archive) is now resolved (squash commit cf92afd confirmed as origin/main HEAD). Separately, three same-day bugs in circuit_breaker.py (c352943, b383135, and this round's #1293) share a common root: the class serves both a sync-only caller (ia_s3.py, checking is_open/record_success/record_failure directly) and async callers (archive.py/engine.py/drain.py, driving state exclusively through allow_request()), and each bug so far involved a state transition that one calling convention exercises but the other does not. This is worth stating as a named pattern so a future round auditing this file (or any other dual sync/async shared-state class) knows to check both calling conventions explicitly, not just the async happy path."
success_signal: "handoffs/handoff-pr-1293-awaiting-ci.md carries status: archived with a resolution field citing the verified merge commit; wiki/continuous-loop-operational-invariants.md gains a new, evidence-linked paragraph (not a rewrite of its existing claims) naming the sync/async dual-caller pattern and citing all three circuit_breaker.py fixes (c352943, b383135, #1293); the extended WikiEntry is committed and pushed to main after local repository/CI revalidation."
status: "achieved"
---

# RunGoal

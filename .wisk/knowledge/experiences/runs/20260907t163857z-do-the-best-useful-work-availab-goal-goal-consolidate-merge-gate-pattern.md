---
goal: "Document the GitHub required-status-check merge gate (e.g. GitGuardian) as a durable Wisk wiki invariant"
id: "run-goals/20260907t163857z-do-the-best-useful-work-availab/goal-consolidate-merge-gate-pattern"
kind: "consolidate-knowledge"
rationale: "This session hit exactly this failure resolving handoff-pr-1277-awaiting-ci's PR #1282 -- a green, no-review-pending, loop-authored PR still failed to merge with an unexplained 405 -- and no prior Experience or wiki entry documented the cause or the fix, so a future round could have wrongly treated the PR as blocked/conflicted and duplicated the work or escalated unnecessarily."
run: "runs/20260907T163857Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "wiki/continuous-loop-operational-invariants.md contains the required-status-check merge-gate pattern and its fix (update_pull_request_branch, then merge), with this run's PR #1282 resolution linked as evidence."
type: "RunGoal"
---

# RunGoal

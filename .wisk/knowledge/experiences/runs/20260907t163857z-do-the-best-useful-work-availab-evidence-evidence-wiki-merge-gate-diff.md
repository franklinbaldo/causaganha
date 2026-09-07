---
type: "RunEvidence"
id: "run-evidence/20260907t163857z-do-the-best-useful-work-availab/evidence-wiki-merge-gate-diff"
run: "runs/20260907T163857Z-do-the-best-useful-work-available-in-this-reposi"
kind: "consolidation"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
summary: "Added a new paragraph and an Evidence & Lineage bullet documenting the GitHub required-status-check (GitGuardian) merge gate discovered while resolving handoff-pr-1277-awaiting-ci this round: merge_pull_request can 405 on a green, no-review PR because a required check never reported on its head SHA (often because the PR sat stale behind an advanced base); update_pull_request_branch retriggers the full required-check suite and unblocks the merge. Diff verified with git diff against the pre-edit file content read earlier in this run."
goal: "run-goals/20260907t163857z-do-the-best-useful-work-availab/goal-consolidate-merge-gate-pattern"
---

# RunEvidence

---
goal: "Land PR #1473 (unify Parquet writer, normalize CNJ, order by numero_processo) on main"
id: "run-goals/20260914t142614z-do-the-best-useful-work-availab/goal-merge-pr-1473"
kind: "task-advance"
rationale: "PR #1473 is the backend-only slice of issue #1469 (parent epic #1468, Parquet nativo CNJ lookup). All 9 CI checks are green and Codex security review completed with no findings, but mergeable_state is 'behind' main (PR #1474 merged after #1473 opened) so it needs an update before merge. Issues #1470-1472 (audit, pilot validation, rollout) all depend on this writer landing first, and #1470's audit already merged on top of an expectation that this normalization exists -- leaving #1473 open blocks the rest of the epic."
run: "runs/20260914T142614Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "PR #1473 is merged to main (merged=true), or if CI turns red after the base-branch update, the failure is diagnosed and a fix is pushed to make it green again."
type: "RunGoal"
---

# RunGoal

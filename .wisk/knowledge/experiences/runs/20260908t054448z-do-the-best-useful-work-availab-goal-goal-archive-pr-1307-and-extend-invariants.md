---
goal: "Confirm PR #1307 is merged into main, archive handoffs/handoff-pr-1307-awaiting-ci, and extend wiki/continuous-loop-operational-invariants.md with a grounded finding: a project's own human-facing architecture doc (FRONTEND.md) can describe files/functions/whole subsystems that never existed, and must be checked against actual file existence and call sites before being trusted or extended."
id: "run-goals/20260908t054448z-do-the-best-useful-work-availab/goal-archive-pr-1307-and-extend-invariants"
kind: "consolidate-knowledge"
rationale: "handoff-pr-1307-awaiting-ci's remaining obligation (merge PR #1307, archive) is now resolved (squash commit ec6a6a9 confirmed as origin/main HEAD, all 10 checks green, zero reviews). The doc-drift finding is a new, distinct category from the wiki entry's existing hazards (all of which are about code, not about a human-facing architecture guide describing nonexistent files/functions as canonical) -- worth recording so a future round auditing or extending FRONTEND.md checks referenced modules actually exist before trusting the doc's own examples."
run: "runs/20260908T054448Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "wiki/continuous-loop-operational-invariants.md gains one new, evidence-linked paragraph (not a rewrite of existing claims) naming the FRONTEND.md doc-drift pattern; handoffs/handoff-pr-1307-awaiting-ci.md carries status: archived with a resolution field citing the verified merge commit; both are committed and pushed to main after local repository/CI revalidation."
type: "RunGoal"
---

# RunGoal

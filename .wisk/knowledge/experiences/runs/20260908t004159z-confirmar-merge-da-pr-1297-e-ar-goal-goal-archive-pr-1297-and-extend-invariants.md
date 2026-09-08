---
goal: "Confirm PR #1297 is merged into main, archive handoffs/handoff-pr-1297-awaiting-ci, and extend wiki/continuous-loop-operational-invariants.md with two grounded findings from this round-family: (1) a fresh container checkout needs 'wisk init .' before 'wisk start' works, now hit independently by two consecutive rounds; (2) reset_manifest's djen_raw omission is a fresh instance of the 'one canonical status field, don't let a mirrored/derived field go stale' hazard."
id: "run-goals/20260908t004159z-confirmar-merge-da-pr-1297-e-ar/goal-archive-pr-1297-and-extend-invariants"
kind: "consolidate-knowledge"
rationale: "handoff-pr-1297-awaiting-ci's remaining obligation (merge PR #1297, archive) is now resolved (squash commit 53cfe59 confirmed as origin/main HEAD). The fresh-checkout wisk-init blocker was independently rediscovered by two consecutive rounds at real diagnosis cost -- worth naming so a third round doesn't repeat it. The reset_manifest bug is a second real, demonstrable instance of trusting a stale mirrored field instead of the one canonical source, worth recording as its own named pattern alongside the wiki entry's existing circuit_breaker.py sync/async pattern."
run: "runs/20260908T004159Z-confirmar-merge-da-pr-1297-e-arquivar-o-handoff"
status: "achieved"
success_signal: "handoffs/handoff-pr-1297-awaiting-ci.md carries status: archived with a resolution field citing the verified merge commit; wiki/continuous-loop-operational-invariants.md gains two new, evidence-linked paragraphs (not a rewrite of its existing claims); the extended WikiEntry is committed and pushed to main after local repository/CI revalidation."
type: "RunGoal"
---

# RunGoal

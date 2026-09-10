---
type: "RunGoal"
id: "run-goals/20260910t041012z-do-the-best-useful-work-availab/goal-confirm-1404-and-extend-invariants"
run: "runs/20260910T041012Z-do-the-best-useful-work-available-in-this-reposi"
kind: "consolidate-knowledge"
goal: "Confirm PR #1404's merge, archive its handoff, and extend the continuous-loop-operational-invariants WikiEntry with a twentieth pattern paragraph plus a lineage bullet for the 'continuing a designated branch past its own squash-merge produces a false merge conflict' hazard."
rationale: "This round hit and resolved a genuine operational obstacle not previously documented: opening a second same-session PR on a designated branch whose first PR was already squash-merged, without resetting the branch first, produces a real GitHub mergeable_state='dirty' -- not a flake, not a review issue, but a git-topology artifact of squash merges losing shared ancestry for touched files. The fix (rebase --onto the new base, force-push) and the diagnostic signature (mergeable_state='dirty' plus 'added in both' on a file from the just-merged PR) need to be durable so a future round recognizes it immediately instead of re-diagnosing from scratch, especially since this session's own git-provider instructions already prescribe the general 'reset a merged designated branch' pattern but this is the first time within the wisk-run history that following the alternative branch-continuation path (needed to string a wiki-confirmation commit onto the same branch as the next Experience round) exposed the conflict this concretely."
success_signal: "wiki/continuous-loop-operational-invariants.md gains a twentieth pattern paragraph plus a lineage bullet referencing runs/20260910T035530Z-... and PR #1404 (squash fba3d7210b7f84bd77747bdf4182ef9a38219d3c); handoffs/handoff-pr-1404-awaiting-ci is archived via wisk handoff continue."
status: "achieved"
---

# RunGoal

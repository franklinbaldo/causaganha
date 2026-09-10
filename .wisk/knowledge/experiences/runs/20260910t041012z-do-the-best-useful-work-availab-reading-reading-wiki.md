---
type: "RunReading"
id: "run-readings/20260910t041012z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260910T041012Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: "Existing WikiEntry, 19 pattern paragraphs, most recently the sibling-config-flag family (check_only -> upload_only)."
finding: "No paragraph yet names the multi-PR-per-session squash-merge continuation hazard hit this round: this session's designated branch (claude/exciting-mccarthy-7cdfgq) had PR #1403 squash-merged, then continued accumulating new commits (the dead-flags fix, the wiki confirmation of #1403, the close-out) directly on top of its own pre-merge history rather than resetting to the new main. Opening PR #1404 from that branch produced mergeable_state='dirty': git's merge-base between the branch and the new origin/main predates the file's introduction, so any file the squashed PR had touched (here, handoffs/handoff-pr-1403-awaiting-ci.md, edited again post-merge to mark it archived) looked like two independent 'added in both' insertions with different content rather than a normal sequential edit. This is a distinct hazard from the already-documented merge-gate pattern (required-status-check 405s) -- it's about branch topology after a squash, not CI status propagation."
---

# RunReading

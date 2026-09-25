---
type: "RunGoal"
id: "run-goals/20260925t202645z-do-the-best-useful-work-availab/goal-resume-pr-1605"
run: "runs/20260925T202645Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Resolve PR #1605's stale merge conflict (issue #1050 segmenter real training corpus, batch 27) and get it back to green/mergeable, then merge; also archive the now-stale handoff-pr-1650-awaiting-ci since PR #1650 already merged."
rationale: "PR #1605 is real, already-reviewed continuity work (TDD RED/GREEN evidence in its own body, 674 additions across 22 files) started by a previous session on 2026-09-24 and never invalidated -- it just went stale (mergeable_state=dirty) because other PRs merged into main afterward. hourly-loop.md's anti-ceremonial-PR rule and the outer task's 'priorize continuidade' instruction both favor finishing already-started, real work over starting something new. handoff-pr-1650-awaiting-ci is dead weight now that its target already merged; leaving it active would mislead a future session into re-checking a resolved question."
success_signal: "PR #1605 head is fast-forwarded past main with no conflict markers, full test suite + ruff + okf-parser check green on the merged branch, and the PR is either merged or has a fresh CI run passing on GitHub; handoff-pr-1650-awaiting-ci is archived via 'wisk handoff continue'."
status: "active"
---

# RunGoal

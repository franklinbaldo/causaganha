---
type: "RunGoal"
id: "run-goals/20260926t062628z-do-the-best-useful-work-availab/goal-shepherd-pr-1670"
run: "runs/20260926T062628Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Shepherd the already-open PR #1670 (segmenter #1051 val/test adjudication slice: review_count 34->37, test_count 4->7) through CI to merge, rather than starting a duplicate adjudication slice concurrently -- and only if it merges cleanly with budget remaining, pick one additional TEST-tilted adjudication slice per the active handoff's next_action."
rationale: "PR #1670 continues the #1051 handoff's own in-flight work (created by the round immediately preceding this one); duplicating its candidate-selection simulation while it's still open risks colliding with documents it already consumed, whereas the #1471 IA-publish track is blocked 13 consecutive rounds with no new signal (see check-handoff-1471-disposition) and not worth another round of identical reconfirmation."
success_signal: "PR #1670 shows state=MERGED with all required checks green; if a follow-on slice is attempted, evidence of a new accepted ReviewRecord (RED test asserting a higher review_count/test_count that failed before ingestion, GREEN after) is committed and pushed."
status: "active"
---

# RunGoal

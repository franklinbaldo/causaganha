---
type: "RunReading"
id: "run-readings/20260907t163857z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260907T163857Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "Recent Experience runs on PR-merge/handoff continuity"
reference: ".wisk/knowledge/experiences/runs/20260907t152500z-fa-a-o-melhor-avan-o-poss-vel-n-outcome-outcome-final.md"
finding: "The immediately preceding round drove 4 already-green, loop-authored PRs (#1277-#1280) to merged and hit real merge conflicts only because three independent rounds had each archived the same stale handoff-pr-1272-awaiting-ci.md on their own branch -- a race pattern, not a code defect. It closed with 0 open PRs and told the next round to re-read issues/PRs fresh. That next-round instruction is what led this run to resume handoff-pr-1277-awaiting-ci and discover PR #1282 (a second, independent race outcome: a still-open, hour-stale PR blocked on a required status check, not a conflict)."
---

# RunReading

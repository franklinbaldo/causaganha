---
type: "RunDecision"
id: "run-decisions/20260917t062515z-do-the-best-useful-work-availab/pivot-from-1471-to-1050"
run: "runs/20260917T062515Z-do-the-best-useful-work-available-in-this-reposi"
question: "Given handoff-issue-1471-ia-publish-pending is blocked on missing IA credentials for a 7th consecutive round with no new information, should this round re-attempt it or pivot to different unblocked work?"
decision: "Pivot to issue #1050 (segmenter corpus growth via TRF2 batch 20). Keep the #1471 handoff open/unchanged for whenever IA write credentials become available."
rationale: "Re-confirming an unchanged, already-well-documented blocker a 7th time produces no new evidence and wastes the round. .wisk/knowledge/wiki/continuous-loop-operational-invariants.md explicitly recommends treating repo/GitHub state as evidence rather than assuming the issue backlog (or a single handoff) is the whole work queue. #1050 is live-confirmed unblocked (21 real TRF2 candidates, correct via a fresh pool scan) and is the documented next tier in knowledge/backlog/issue-1050.md's own unblock_condition."
---

# RunDecision

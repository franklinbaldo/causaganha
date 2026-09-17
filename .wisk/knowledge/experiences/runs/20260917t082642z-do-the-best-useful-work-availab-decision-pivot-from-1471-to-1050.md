---
type: "RunDecision"
id: "run-decisions/20260917t082642z-do-the-best-useful-work-availab/pivot-from-1471-to-1050"
run: "runs/20260917T082642Z-do-the-best-useful-work-available-in-this-reposi"
question: "Given handoff-issue-1471-ia-publish-pending is blocked on missing IA credentials and an unreachable baseline commit for an 8th+ consecutive round with no new information, should this round re-attempt it or pivot to different unblocked work?"
decision: "Pivot to issue #1050 (segmenter corpus growth, batch 21, TRF2). Keep the #1471 handoff open/unchanged for whenever IA write credentials become available."
rationale: "Re-confirming an unchanged, already well-documented blocker produces no new evidence and wastes the round. knowledge/backlog/issue-1050.md documents TRF2 as the next live-confirmed unblocked tier (store_count=4 after batch20, live pool re-scanned this round to 6 fresh Acordao candidates >=2500 chars after cleaning, none previously ingested). This mirrors the disposition already used successfully by the prior round (runs/20260917T062515Z...)."
---

# RunDecision

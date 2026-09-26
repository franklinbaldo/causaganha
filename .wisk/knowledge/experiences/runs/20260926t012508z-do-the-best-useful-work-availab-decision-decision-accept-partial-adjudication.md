---
type: "RunDecision"
id: "run-decisions/20260926t012508z-do-the-best-useful-work-availab/decision-accept-partial-adjudication"
run: "runs/20260926T012508Z-do-the-best-useful-work-available-in-this-reposi"
question: "The goal's success_signal asked for review_count to increase by 2. Only 1 of 2 target documents produced a valid adjudicated ReviewRecord this round -- should the round accept +1 as real progress, or keep spending budget trying to force the second document through?"
decision: "Accept +1 (review_count 31->32, test_count 2->3) as genuine, mechanically-verified progress and stop attempting the second document (doc_82d8ee7168b24d787ce0417f888d1eb3) after 2 failed independent-annotation attempts; do not lower verification standards to force it through, and do not spend a third subagent dispatch chasing it this round."
rationale: "Both TJPB attempts had real, code-caught defects (a dropped clause + normalized quotes on attempt 1; 5x duplicate single-anchor resultado tags + an overlapping fundamentacao_legal span + an undeclared unmatched relatorio pair on attempt 2) -- these are exactly the mechanical/verbatim guards RFC 0012 Sec 11 exists to catch, and ingesting a defective annotation just to hit a round-level number would corrupt the dataset the whole #1051 effort exists to keep trustworthy. One verified success is real, durable progress (the RFC 0012 floor math means every genuine review matters); a rushed second one is not. This mirrors the project's own established practice across dozens of prior segmenter batches: reject and redo rather than patch around a verbatim-fidelity failure."
---

# RunDecision

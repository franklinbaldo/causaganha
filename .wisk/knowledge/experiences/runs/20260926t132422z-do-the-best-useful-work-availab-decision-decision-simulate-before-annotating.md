---
type: "RunDecision"
id: "run-decisions/20260926t132422z-do-the-best-useful-work-availab/decision-simulate-before-annotating"
run: "runs/20260926T132422Z-do-the-best-useful-work-available-in-this-reposi"
question: "Which candidates should this round adjudicate, and how do we know they'll actually move test_count without colliding with the concurrent PR #1682?"
decision: "doc_3f6fbeed801469206bd017a34cec4d15 (TJMS, 2696 chars), doc_6129fdd7ecf441fb4629fd2476197bfa (TRF2, 2757 chars), doc_e2986082e14face4a4120f6de20e2248 (TRF2, 2791 chars) -- the 3 shortest documents among 121 eligible single-annotated/seeded_with==none/unreviewed candidates (excluding PR #1682's 4 in-flight document_ids), confirmed by a joint assign_splits simulation to raise test_count from 18 to 21 (val_count unchanged at its 30 ceiling)."
rationale: "assign_splits recomputes the whole val/test partition from a fixed hash order of (seed, group_id) every run -- the aggregate counts are the checkable contract, not which specific document lands in val vs test. Simulating first avoids spending annotation effort on a candidate that wouldn't move the metric. PR #1682 (open, same day, same track, CI pending) already claims doc_52ca8d9d94f86a8426e0e9c3c7ef158b/doc_6b9ee9d4f525b8442af4cbc20da41269/doc_7e91843200b79e7467d0ae541ad9c6c8/doc_c41321b105269252919a5d4d730800a2 -- excluded from this round's candidate pool to avoid duplicating work or racing on the same documents (concurrent same-day rounds on this track have happened before without conflict precisely because their document sets never overlapped)."
goal: "run-goals/20260926t132422z-do-the-best-useful-work-availab/goal-1051-next-batch"
---

# RunDecision

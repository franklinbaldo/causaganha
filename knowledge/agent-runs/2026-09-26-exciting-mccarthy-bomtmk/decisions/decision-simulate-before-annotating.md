---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-bomtmk-decision-simulate-before-annotating"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
question: "Which 3 of the 136 eligible candidates should this round adjudicate, and how do we know they'll actually move test_count rather than just review_count?"
choice: "doc_8904b2884e6177d2b61fd7462ce7539d (TRF2, sentenca, 2082 chars), doc_6b29f96e41baeb5405c87bd09fb38d3d (TJES, sentenca, 2104 chars), doc_de65a409f2156cc18d43f96fa35347fc (TJSE, acordao, 2161 chars) -- the three shortest documents among the 129 candidates that individually raise test_count in an isolated assign_splits simulation, further confirmed by a joint simulation of all three together (test_count 7->10, val_count unchanged at 30, its ceiling)."
rationale: "assign_splits recomputes the entire val/test partition from a fixed hash of (seed, group_id) on every call -- which specific document lands in val vs test is not identity-controllable, only the aggregate counts are a real, checkable contract (established by rounds p08457/kgxf50, reconfirmed here). Simulating both in isolation AND jointly before spending any annotation effort avoids adjudicating documents that only move val_count (already at its ceiling) or that individually look promising but net to zero once combined. Shortest-first is the same tractability heuristic used by prior rounds -- it bounds reading/annotation effort per document within this round's time budget without biasing which categories get represented (2 sentenca + 1 acordao, 3 distinct tribunals: TRF2/TJES/TJSE)."
---

# Decision: candidate selection via simulate-before-annotate

Ran a scratch script (`segmenter_dataset.splits.assign_splits` against
the live `data/segmenter` store) to enumerate the 136 single-annotated,
`seeded_with=='none'`, unreviewed documents, then simulated adding each
one in isolation to `evaluation_eligible`: 129 of 136 individually raise
`test_count`. Picked the 3 shortest of those 129 for tractability, then
re-ran the simulation with all 3 added jointly to confirm the aggregate
effect before committing to the annotation work: `val_count` unchanged
at 30 (its ceiling), `test_count` 7->10.

```
Total documents: 197, candidates: 136
Base val=30 test=7
Candidates individually raising test_count: 129 of 136
Joint simulation with the 3 picked documents: val=30 test=10
```

---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-kgxf50-decision-simulate-before-annotating"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
question: "Which 3 of the 139 eligible candidates should this round adjudicate, and how do we know they'll actually move test_count rather than just review_count?"
choice: "doc_d3de3dfe95769791db33077c54bd3724 (TJSC), doc_4a8e16820fb9c8fa1d808d717d9a34d7 (TJMG), doc_3b0be436ba6753185997c37b2b6b9765 (TJSE) -- the three shortest documents (1037/1623/2028 chars) among the 132 candidates that individually raise test_count in an isolated assign_splits simulation, further confirmed by a joint simulation of all three together (test_count 4->7, val_count unchanged at 30, its ceiling)."
rationale: "assign_splits recomputes the entire val/test partition from a fixed hash of (seed, group_id) on every call -- which specific document lands in val vs test is not identity-controllable, only the aggregate counts are a real, checkable contract (established by round p08457, reconfirmed here). Simulating both in isolation AND jointly before spending any annotation effort avoids the failure mode of adjudicating documents that only move val_count (already at its ceiling, so wasted effort) or that individually look promising but net out to zero once combined with each other. Shortest-first is the same tractability heuristic used by round p08457 -- it bounds the reading/annotation effort per document within this round's time budget without biasing which categories get represented (both acordao and sentenca types, 3 distinct tribunals not yet locked to any one family)."
---

# Decision: candidate selection via simulate-before-annotate

Ran a scratch script (`segmenter_dataset.splits.assign_splits` against
the live `data/segmenter` store) to enumerate the 139 single-annotated,
`seeded_with=='none'`, unreviewed documents, then simulated adding each
one in isolation to `evaluation_eligible`: 132 of 139 individually raise
`test_count`. Picked the 3 shortest of those 132 for tractability, then
re-ran the simulation with all 3 added jointly to confirm the aggregate
effect before committing to the annotation work: `val_count` unchanged
at 30 (its ceiling — expected, no room left there), `test_count` 4->7.

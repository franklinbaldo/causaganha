---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-sg2540-decision-simulate-before-annotating"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
question: "Which candidates should this round adjudicate, and how do we know they'll actually move test_count rather than just review_count?"
choice: "doc_6b9ee9d4f525b8442af4cbc20da41269 (TRF4, 2477 chars), doc_c41321b105269252919a5d4d730800a2 (TJMS, 2508 chars), doc_7e91843200b79e7467d0ae541ad9c6c8 (TJPI, 2552 chars), doc_52ca8d9d94f86a8426e0e9c3c7ef158b (TJES, 2583 chars) -- the four shortest documents among 130 candidates that individually raise test_count in an isolated assign_splits simulation, further confirmed by a joint simulation of all four together (test_count 18->22, val_count unchanged at 30, its ceiling)."
rationale: "assign_splits recomputes the whole val/test partition from a fixed hash order of (seed, group_id) every run -- which specific document lands in val vs test isn't identity-controllable, only the aggregate counts are the real, checkable contract (per knowledge/backlog/issue-1051.md's established method). Simulating first avoids spending real annotation/adjudication effort on a candidate that wouldn't move the metric, and the candidate pool shrinks with every concurrent round, so a cached count from even a few minutes earlier can't be trusted."
---

# Decision: simulate before spending annotation effort

Scanned 137 single-annotated/`seeded_with=='none'`/unreviewed
candidates live at round start; 130 individually raised `test_count`.
Picked the 4 shortest for tractability (2477/2508/2552/2583 chars);
a joint simulation confirmed `test_count` 18->22 before any subagent
was dispatched. Post-ingestion, the real governance status matched
this simulation exactly (`test_count` 18->22, `review_count` 48->52).

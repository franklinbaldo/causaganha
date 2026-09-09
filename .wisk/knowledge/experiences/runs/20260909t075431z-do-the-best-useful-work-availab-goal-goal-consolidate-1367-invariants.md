---
goal: "Archive handoffs/handoff-pr-1367-awaiting-ci (already confirmed resolved above) and extend the continuous-loop-operational-invariants WikiEntry with the two generalizable lessons this round's segmenter-audit repair surfaced: (1) an audit heuristic finding is a candidate for review, not a confirmed defect -- verify against real document semantics before force-fixing; (2) this store's mechanical validation forbids any label overlap across all categories, not just same-category, so a plausible new annotation span can silently collide with an unrelated region's short cue text and needs checking before writing."
id: "run-goals/20260909t075431z-do-the-best-useful-work-availab/goal-consolidate-1367-invariants"
kind: "consolidate-knowledge"
rationale: "Both lessons are directly reusable by #1050's remaining, much larger scope (mining rare-category documents, scaling the corpus to 25/50/100+ train docs) -- the exact same annotation-adding mechanics this round hit repeatedly (3 of 13 repairs needed a planned span dropped after an overlap error) will recur at much higher volume there, and the false-positive-heuristic lesson prevents a future round from blindly tagging to satisfy count(...)>N regardless of real semantics."
run: "runs/20260909T075431Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "The WikiEntry file has a new paragraph (or paragraphs) under Summary plus a matching Evidence & Lineage bullet for this round; the handoff is archived with the merge commit SHA; okf-parser check on .wisk/knowledge stays conformant."
type: "RunGoal"
---

# RunGoal

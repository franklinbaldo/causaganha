---
type: "RunReading"
id: "run-readings/20260909t075431z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260909T075431Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "Existing invariant: cross-session PR continuation goes through explicit Wisk handoffs, and a resuming session must reconstruct factual repo/GitHub state rather than trust the handoff's recorded baseline at face value. This round followed that exactly: handoff-pr-1367-awaiting-ci's baseline (repository_head eaa79a9b) was stale by two commits (a docs push and the merge itself) by the time this round re-verified it via git fetch + PR read."
---

# RunReading

---
type: "RunReading"
id: "run-readings/20260909t164153z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260909T164153Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "13 recorded root-cause-family patterns plus full lineage through PR #1381. No entry yet for this session's own finding: a business-day-filter inconsistency between two loops in the same function reading the same set (velocityCalc.ts), and the specific hazard that a documented 'X can never happen' invariant comment (repeated 3x) was contradicted by a rarely-taken code path (prune()'s already-uploaded exception) elsewhere in the same codebase -- a variant of the doc-drift/dead-invariant patterns already recorded (patterns 6/7 duplicated-classification-logic, and the FRONTEND.md doc-drift family) but distinct: here the false invariant lived in code comments read by both humans and agents, not a separate prose doc, and the two consumers of the same claimed invariant (two loops in one function) silently diverged instead of one obviously-stale doc section."
---

# RunReading

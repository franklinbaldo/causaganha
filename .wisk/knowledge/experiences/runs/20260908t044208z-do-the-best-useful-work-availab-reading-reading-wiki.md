---
type: "RunReading"
id: "run-readings/20260908t044208z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260908T044208Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "Existing WikiEntry documents: Wisk-owns-orchestration philosophy; the .wisk/ canonical namespace history; explicit cross-session PR continuation via Handoffs; the GitGuardian-required-check-needs-branch-update pattern; RunOutcome.next_move as a legitimate work source; the sync/async dual-calling-convention hazard in circuit_breaker.py (three same-day bugs sharing one root cause); the reset_manifest canonical-field-not-cleared hazard; and the wisk init . before wisk start fix for a fresh checkout's missing knowledge/system/. No entry yet documents the class of bug just fixed this round: a domain exception introduced for one call site (DJENRateLimitedError, defined alongside get_caderno_url) not being caught at every sibling call site that can raise it (drain.py omitted it while engine.py and probe.py already had it) -- a distinct but related hazard to the sync/async dual-caller pattern already documented, worth adding as its own generalizable lesson."
---

# RunReading

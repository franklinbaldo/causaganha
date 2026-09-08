---
type: "RunReading"
id: "run-readings/20260908t063932z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260908T063932Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "Existing durable Wisk wiki state"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "One WikiEntry exists, covering (among other lessons): the fresh-checkout 'wisk init .' requirement; the GitGuardian required-check merge pattern; a RunOutcome's next_move as a legitimate work source; the circuit_breaker.py sync/async dual-caller hazard; reset_manifest's canonical-vs-mirrored-field hazard; drain.py's missed DJENRateLimitedError catch; and the FRONTEND.md Tier-0 doc-drift finding from PR #1307 (nonexistent useDashboard.svelte.ts/buildTimeData.ts documented as canonical). None of these entries cover this round's finding: an orphaned Astro component whose only styling referenced a CSS custom property (--pico-muted-border-color) belonging to a design system (Pico CSS) that a prior, unrelated migration (the Cobogo/Panda reboot, #1169) had already fully removed from the codebase -- the dead-code-detection lesson and the design-system-migration-leaves-stale-references lesson are each individually covered elsewhere in the wiki's lineage (PR #1300's TribunalCalendar.svelte, PR #1307's FRONTEND.md prose) but never as the same finding occurring together in one file, nor is the specific fact that FRONTEND.md's entire dedicated Pico CSS section is now stale (a bigger doc-drift item than any single fixed file) yet recorded."
---

# RunReading

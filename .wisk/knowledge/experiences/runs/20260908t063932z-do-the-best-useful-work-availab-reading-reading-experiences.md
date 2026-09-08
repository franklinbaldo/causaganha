---
type: "RunReading"
id: "run-readings/20260908t063932z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260908T063932Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "Most recent Experience run"
reference: "../runs/20260908T062514Z-do-the-best-useful-work-available-in-this-reposi.md"
finding: "The immediately prior Experience run (20260908T062514Z) re-verified the 17-issue backlog as environment-blocked and no open PRs/handoffs, then investigated the previous round-family's next_move (a spot-check on FRONTEND.md's other sections for the same doc-drift pattern fixed in PR #1307's Tier 0). It found web/src/components/TribunalCoverageGrid.astro was entirely unreferenced dead code that also styled itself with the now-nonexistent Pico CSS variable --pico-muted-border-color, deleted it, verified the full web suite/typecheck/lint/build stayed green, and landed it as PR #1309 (now merged, sha 4a77670). Its own next_move flagged a larger, not-yet-addressed lead: FRONTEND.md's 'Tech Stack Overview' table and entire 'Pico CSS — Semantic HTML as the First Styling Layer' section (~70 lines) still document Pico CSS as the canonical styling system, even though Pico is fully removed from the toolchain."
---

# RunReading

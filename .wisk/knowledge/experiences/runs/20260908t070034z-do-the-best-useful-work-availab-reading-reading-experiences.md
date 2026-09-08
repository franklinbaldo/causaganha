---
type: "RunReading"
id: "run-readings/20260908t070034z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260908T070034Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "Most recent Experience run"
reference: "../runs/20260908T064732Z-do-the-best-useful-work-available-in-this-reposi.md"
finding: "The immediately prior Experience run (20260908T064732Z) picked up its own round-family's next_move (spot-check FRONTEND.md's Pico CSS section for the same drift pattern already fixed twice this session: PR #1307's Tier 0, PR #1309's dead --pico- variable). Confirmed the whole Pico CSS section was stale by reading node_modules/cobogo/preset/index.mjs directly (no automatic element styling beyond html/body/::selection/a), and while verifying also found two further related instances: a fabricated token-name example and an entire fictional 'Theming' (data-theme light/dark toggle) subsection that issue #1178 had already deliberately removed (guarded by themeSingleModeGuard.test.ts), plus a doc example citing the deleted ThemeToggle.astro. Rewrote all of it with grep-verified real examples, preserving the still-valid accessibility guidance under a Pico-independent heading. Landed as PR #1311 (now merged, sha 0511310). Its own next_move: three consecutive rounds fixing the same doc-drift-in-FRONTEND.md pattern suggests a final read-through of the doc's remaining sections (Zod, DOMPurify, DuckDB, Testing, TypeScript, Known Gaps) against real code is worthwhile if no other lead surfaces, since the doc has been wrong three-for-three times checked so far."
---

# RunReading

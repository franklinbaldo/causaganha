---
goal: "Rewrite FRONTEND.md's Tech Stack Overview Styling row and its entire 'Pico CSS — Semantic HTML as the First Styling Layer' section (plus the adjacent 'Vanilla CSS and Design Tokens' section's now-inaccurate claims) to describe the actual live styling system: Panda CSS via the cobogo preset."
id: "run-goals/20260908t064732z-do-the-best-useful-work-availab/goal-fix-frontend-md-pico-css-drift"
kind: "task-advance"
rationale: "Flagged as this round-family's own next_move after PR #1309 deleted an orphaned component that referenced a dead Pico CSS variable. Verified the claim independently: Pico CSS is not in web/package.json, no <link> imports it anywhere, and grep confirms zero --pico-*/--tinta-* variables exist in web/src (matching CLAUDE.md's CSS token boundary section). Inspected node_modules/cobogo/preset/index.mjs directly: it defines globalCss only for html/body/::selection/a -- there is no element-level auto-styling for button/table/article/fieldset/mark/kbd/nav/data the way Pico provided. Every one of FRONTEND.md's Pico-era claims (the semantic-HTML-gets-styled-for-free model, the anti-pattern table naming Pico as the reason to use certain elements, the Tech Stack table row) is now false about how this codebase actually works, and a contributor trusting this section would write code assuming automatic styling that does not exist."
run: "runs/20260908T064732Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "FRONTEND.md's Styling table row and Pico CSS section no longer mention Pico; the replacement section documents the cobogo preset's actual recipes (button/card/badge/alert/input/article/table/navLink) and css() token usage with real, grep-verified examples from web/src/pages/*.astro; a repo-wide grep for 'Pico' in FRONTEND.md returns no remaining references to it as the live system; npm run typecheck/lint/test/build stay green (docs-only change, but confirming no accidental code touch)."
type: "RunGoal"
---

# RunGoal

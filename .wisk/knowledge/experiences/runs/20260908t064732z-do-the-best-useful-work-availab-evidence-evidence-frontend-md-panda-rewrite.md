---
type: "RunEvidence"
id: "run-evidence/20260908t064732z-do-the-best-useful-work-availab/evidence-frontend-md-panda-rewrite"
run: "runs/20260908T064732Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "FRONTEND.md"
summary: "Replaced the Tech Stack Overview Styling row and the entire 'Pico CSS — Semantic HTML as the First Styling Layer' section with a new 'Panda CSS — Tokens and Recipes as the First Styling Layer' section, documenting the cobogo preset's real recipes (button/card/badge/alert/input/article/table/navLink, with variant lists read directly from node_modules/cobogo/preset/index.mjs) and css() token usage, all examples grep-verified against real call sites (stats.astro, sobre.astro, explorador.astro, processo.astro, index.astro, Layout.astro). Preserved the genuinely still-valid, actively-followed accessibility guidance (fieldset+legend, kbd-outside-label, role=search, nav-as-landmark -- confirmed in use in SearchFilters.svelte/SmartSearchInput.svelte/IASearchBar.svelte) under a new Pico-independent 'Semantic HTML — accessibility patterns' heading rather than deleting it. Rewrote 'Vanilla CSS and Design Tokens' (now 'index.css — the Legacy-Svelte-Island CSS Bridge') to match CLAUDE.md's actual CSS token boundary description, replaced the fictional --space-4/--color-base-100/--radius-card/--font-size-sm token example with real --s-4/--color-surface/--cg-text names from index.css, and removed the fabricated 'Theming' subsection (data-theme/causaganha/causaganhadark) -- discovered via grep that index.css has zero data-theme selectors and that web/src/lib/themeSingleModeGuard.test.ts documents issue #1178's single-theme decision with a regression test forbidding exactly those markers. Fixed the Astro-island example citing the deleted ThemeToggle.astro (confirmed nonexistent) with the real, still-existing NetworkStatusBanner.astro. Fixed the Svelte section's design-token-availability claim and the CSS anti-patterns list to stop pointing at index.css/Pico as canonical."
goal: "run-goals/20260908t064732z-do-the-best-useful-work-availab/goal-fix-frontend-md-pico-css-drift"
---

# RunEvidence

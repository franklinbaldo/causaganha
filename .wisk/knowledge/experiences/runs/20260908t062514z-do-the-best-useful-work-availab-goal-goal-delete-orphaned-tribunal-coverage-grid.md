---
goal: "Delete the orphaned TribunalCoverageGrid.astro component and confirm no regression"
id: "run-goals/20260908t062514z-do-the-best-useful-work-availab/goal-delete-orphaned-tribunal-coverage-grid"
kind: "task-advance"
rationale: "Grep-verified TribunalCoverageGrid.astro is imported/referenced by zero other files in the repository (components, pages, tests, docs) -- it is unreachable dead code, matching the exact precedent of PR #1300's TribunalCalendar.svelte deletion. It also hardcodes 'background: var(--pico-muted-border-color)', a CSS custom property from the Pico CSS design system that CLAUDE.md's CSS token boundary section states was fully replaced by Panda CSS/the cobogo preset (Pico is not in package.json, and grep confirms no --pico-* variable is defined anywhere in web/src); the swatch would render with no visible background even if the component were ever wired up. Deleting dead code with a design-system reference to a system that no longer exists is a real, bounded improvement with no product behavior change."
run: "runs/20260908T062514Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "web's full test suite, astro check, eslint, and astro build all remain green after removing the file, and a repo-wide grep for 'TribunalCoverageGrid' returns no remaining references."
type: "RunGoal"
---

# RunGoal

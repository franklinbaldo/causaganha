---
type: "RunGoal"
id: "run-goals/20260908t102544z-do-the-best-useful-work-availab/goal-fix-auto-grid-css-bridge"
run: "runs/20260908T102544Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Restore .auto-grid/.auto-grid-sm in web/src/index.css and migrate DuckDBExplorer.svelte's two remaining Pico-era class=\"grid\" usages to .auto-grid, fixing a live layout regression left over from the Cobogo/Panda reboot (#1169) that deleted styles/base.css (which defined these utilities) and the Pico import (which gave bare .grid its native semantic-grid behavior) without migrating the 8 component files still referencing them."
rationale: "This is a real, currently-live UI defect (not just doc drift): DuckDBExplorer, SearchFilters, TribunalStatsBar, VelocityTimeline, HeatmapMonthPicker, TribunalDetail and YearSummaryCards all render these wrappers as plain block stacks with zero grid layout on every viewport, since #1169, because no CSS anywhere defines .auto-grid/.auto-grid-sm/.grid. Grep-verified across the whole web/src tree; git archaeology (git show 2c497c9^:web/src/styles/base.css) confirms both utilities existed pre-migration and were deleted along with base.css."
success_signal: "A new Vitest regression test (web/src/lib/autoGridBridge.test.ts) asserts index.css defines .auto-grid/.auto-grid-sm and that no source file uses the removed class=\"grid\"; RED before the fix (2/3 failing), GREEN after (3/3 passing), and the full web suite (70 files / 504 tests) plus typecheck/lint stay clean."
status: "active"
---

# RunGoal

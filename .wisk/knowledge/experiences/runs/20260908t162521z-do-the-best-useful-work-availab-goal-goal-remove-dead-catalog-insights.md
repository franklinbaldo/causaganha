---
goal: "Remove the dead 'Catalog' API surface from web/src/lib/coverageInsights.ts (summarizeCatalogDay, filterCoverageDays, countCoverageFilters, getDayStatusLabel, buildCatalogAttentionCards, and the CoverageFilter/CompletedCatalogDay/CoverageDaySummary types)."
id: "run-goals/20260908t162521z-do-the-best-useful-work-availab/goal-remove-dead-catalog-insights"
kind: "task-advance"
rationale: "Prior round's next_move flagged buildCatalogAttentionCards's calendar-day (not business-day) heuristics as a possible bug but deferred because the function might be dead code with zero call sites. Repo-wide grep confirms it: the only importers of coverageInsights.ts (TribunalDetail.svelte and its own test file) use exclusively buildTribunalAttentionCards -- every other export, and the calendar-day bug inside it, is unreachable from any page or test. Per this loop's established pattern (PR #1267 ZipInventory, PR #1309 TribunalCoverageGrid.astro), confirmed-dead code is removed rather than debugged, since a fix to code nothing calls delivers zero product value and the deletion itself is the safe, real advance."
run: "runs/20260908T162521Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "web/src/lib/coverageInsights.ts contains only buildTribunalAttentionCards plus the AttentionCard type it and callers need; a repo-wide grep for the removed export names returns zero matches outside git history; full web suite (npm run test / typecheck / lint / build) stays green before and after."
type: "RunGoal"
---

# RunGoal

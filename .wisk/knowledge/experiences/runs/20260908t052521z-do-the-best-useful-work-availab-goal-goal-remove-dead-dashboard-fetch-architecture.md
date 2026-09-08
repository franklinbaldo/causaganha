---
goal: "Delete the abandoned fetchAllData/deriveData/useDashboardWithPolling dashboard-data architecture (dead code plus fictional documentation) and correct FRONTEND.md to describe the loadContract()/readJson() pattern pages actually use."
id: "run-goals/20260908t052521z-do-the-best-useful-work-availab/goal-remove-dead-dashboard-fetch-architecture"
kind: "task-advance"
rationale: "With the 17-issue backlog re-confirmed environment-blocked and no open PRs/handoffs, the prior round's outcome next_move flagged fetchData.ts's ~200 lines of unreferenced exports as a lead. Investigating it uncovered a larger, confirmed inconsistency: FRONTEND.md documents fetchAllData/deriveData/DerivedData/useDashboardWithPolling (from a useDashboard.svelte.ts file that does not exist) and buildTimeData.ts/loadBuildTimeData (also nonexistent) as current or actively-used canonical architecture, with concrete code samples attributed to real files (TribunalDetail.svelte, [tribunal].astro) that were independently verified to use a completely different pattern (loadContract() query contracts + readJson()). QUERY_KEYS.dashboard/dashboardMeta/pipelineRuns/pipelineToday in queryKeys.ts are correspondingly unused. This is exactly the 'inconsistências entre código e knowledge' category worth fixing: a future session trusting FRONTEND.md would try to import files that do not exist."
run: "runs/20260908T052521Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "grep -rn 'fetchAllData\\|deriveData(\\|startLivePolling\\|getArchiveSnapshot\\|useDashboardWithPolling\\|useDashboard.svelte\\|buildTimeData' web/src FRONTEND.md returns no matches (fetchWithRetry/FallbackResponse remain); web/src/lib/queryKeys.ts exports only iaCoverage and djenSearch; uv run --directory web npm run test and npm run build (or the project's equivalent typecheck) stay green after the removal."
type: "RunGoal"
---

# RunGoal

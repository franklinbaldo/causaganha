---
type: "RunOutcome"
id: "run-outcomes/20260908t052521z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260908T052521Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "partial"
summary: "Investigated the prior round's next_move lead (fetchData.ts's ~200 unreferenced lines) and found it was one symptom of a larger, confirmed architecture/documentation drift: FRONTEND.md documented fetchAllData/deriveData/DerivedData/useDashboardWithPolling (from a useDashboard.svelte.ts file that does not exist) and a planned buildTimeData.ts/loadBuildTimeData helper (also nonexistent) as current, canonical dashboard-fetch architecture, with code samples misattributed to real files ([tribunal].astro, TribunalDetail.svelte) independently verified to already use the current loadContract()/readJson() pattern instead. Removed the dead code (fetchAllData/deriveData/startLivePolling/getArchiveSnapshot/DerivedData/CacheData/VelocityMetrics from fetchData.ts, keeping fetchWithRetry/FallbackResponse; QUERY_KEYS.dashboard/dashboardMeta/pipelineRuns/pipelineToday from queryKeys.ts, keeping iaCoverage/djenSearch used by AnnualCoverageMonitor.svelte/PublicationSearch.svelte) and rewrote every affected FRONTEND.md section (Tier-0 build-time-seed example, the TanStack 'Dashboard queries with meta.json polling' subsection, Data Fetching section, TypeScript any-carve-out, Known-gaps bullets) with examples drawn from real, verified call sites. Full web suite (66 files / 493 tests), astro check (0 errors), eslint (0 errors), astro build (120 pages), and ruff check all green after the change; a repo-wide grep confirmed zero remaining references to every removed symbol. Landed as PR #1307 against main; work_status=partial because CI on the new head is still pending at report time (see handoff-pr-1307-awaiting-ci)."
next_move: "Resume via handoff-pr-1307-awaiting-ci: watch PR #1307's CI, merge once green (squash), and archive the handoff. If a future round wants a further pass on this same area: web/src/lib/readJson.ts and duckdbSingleton.ts were confirmed real/used during this investigation (not further leads), but nobody has audited whether FRONTEND.md's other tiers (1-3 under 'Four tiers of state') have similar drift the way Tier 0 did -- worth a spot-check next time docs are touched. The 17-issue backlog remains environment-blocked (re-verify fresh rather than trusting this note)."
goals_advanced: ["run-goals/20260908t052521z-do-the-best-useful-work-availab/goal-remove-dead-dashboard-fetch-architecture"]
evidence: ["run-evidence/20260908t052521z-do-the-best-useful-work-availab/evidence-diff-remove-dead-architecture"]
checks: ["run-checks/20260908t052521z-do-the-best-useful-work-availab/check-web-suite-green"]
experiences_recorded: []
---

# RunOutcome

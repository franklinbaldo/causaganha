---
type: "RunEvidence"
id: "run-evidence/20260908t052521z-do-the-best-useful-work-availab/evidence-diff-remove-dead-architecture"
run: "runs/20260908T052521Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "web/src/lib/fetchData.ts, web/src/lib/queryKeys.ts, web/src/components/__steps__/shared.ts, FRONTEND.md"
summary: "Removed fetchAllData/deriveData/startLivePolling/getArchiveSnapshot/CacheData/DerivedData/VelocityMetrics (and their sole private helpers resolve/resolveIA/safeFetch/BASE/IA_BASE) from fetchData.ts, keeping fetchWithRetry/FallbackResponse; dropped the correspondingly-unused QUERY_KEYS.dashboard/dashboardMeta/pipelineRuns/pipelineToday from queryKeys.ts; dropped the now-pointless fetchAllData mock in shared.ts; rewrote every FRONTEND.md section that documented the abandoned useDashboard.svelte.ts/buildTimeData.ts architecture (Tier 0 build-time seed example, 'Dashboard queries with meta.json polling' subsection, Data Fetching section, TypeScript DerivedData carve-out, Known-gaps bullets) to describe the loadContract()/readJson() + fetchAllTribunalMetadata()-style per-query pattern actually used by [tribunal].astro/TribunalDetail.svelte/AnnualCoverageMonitor.svelte."
goal: "run-goals/20260908t052521z-do-the-best-useful-work-availab/goal-remove-dead-dashboard-fetch-architecture"
---

# RunEvidence

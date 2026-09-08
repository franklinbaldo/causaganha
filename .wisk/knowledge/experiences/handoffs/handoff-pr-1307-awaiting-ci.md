---
type: "Handoff"
id: "handoffs/handoff-pr-1307-awaiting-ci"
title: "Confirmar merge da PR #1307 (remove abandoned dashboard-fetch architecture, fix FRONTEND.md drift)"
created_at: "2026-09-08T05:39:31.084406Z"
status: "active"
created_by_run: "runs/20260908T052521Z-do-the-best-useful-work-available-in-this-reposi"
state: "active"
next_action: "PR #1307 (https://github.com/franklinbaldo/causaganha/pull/1307) opened from claude/exciting-mccarthy-5oak6k onto main: removes dead fetchAllData/deriveData/startLivePolling/getArchiveSnapshot/DerivedData/CacheData from fetchData.ts and the unused QUERY_KEYS.dashboard/dashboardMeta/pipelineRuns/pipelineToday from queryKeys.ts, and rewrites the FRONTEND.md sections that documented that abandoned architecture (including a useDashboard.svelte.ts/buildTimeData.ts pattern that never existed in the repo) to describe the loadContract()/readJson() pattern pages actually use. Full web suite (66/66 files, 493/493 tests), astro check, eslint, astro build, and ruff check were all green locally before opening the PR. A resuming session should: (1) check current PR/CI state fresh rather than trust this note if stale, (2) if CI is red, diagnose and push a fix, (3) if a required status check (e.g. GitGuardian) is missing on an otherwise-green head, update the branch from main to re-trigger it (see wiki/continuous-loop-operational-invariants), (4) once merged, archive this Handoff via 'wisk handoff continue'."
references: []
goals: ["run-goals/20260908t052521z-do-the-best-useful-work-availab/goal-remove-dead-dashboard-fetch-architecture"]
repository_head: "8384c66e829c1dad27aceb8d0d0aaf386bb95b63"
repository_branch: "claude/exciting-mccarthy-5oak6k"
repository_dirty: false
repository_diff_digest: ""
---

# Handoff

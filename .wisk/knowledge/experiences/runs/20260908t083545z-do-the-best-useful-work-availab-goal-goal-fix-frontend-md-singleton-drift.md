---
goal: "Fix FRONTEND.md doc drift: 'State Architecture' and the 'Decision Ladder' cite a nonexistent completedItemsStore.svelte.ts / .svelte.ts-with-$state singleton-lazy-loader pattern that has zero instances anywhere in web/src."
id: "run-goals/20260908t083545z-do-the-best-useful-work-availab/goal-fix-frontend-md-singleton-drift"
kind: "task-advance"
rationale: "This is the next_move flagged by the prior run's RunOutcome (FRONTEND.md wrong 3/3 times checked in this session); grep confirms zero '*.svelte.ts' files exist anywhere in web/src and 'completedItemsStore' has no git history at all, so the doc's cited example and its generalized Decision-Ladder rule are both fictional, matching the exact doc-drift pattern already fixed in PR #1307/#1309/#1311."
run: "runs/20260908T083545Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A repo-wide 'find web/src -iname *.svelte.ts' still returns nothing (no code changed), but FRONTEND.md's State Architecture section and Decision Ladder step 3 cite a real, grep-verified existing singleton file (e.g. queryClient.ts or duckdbSingleton.ts) and describe the actual plain-.ts module-level-variable-plus-getter pattern instead of the nonexistent .svelte.ts/$state mechanism; web test suite stays green after the edit."
type: "RunGoal"
---

# RunGoal

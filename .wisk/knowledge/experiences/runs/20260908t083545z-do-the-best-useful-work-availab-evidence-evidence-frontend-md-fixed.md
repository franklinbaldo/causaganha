---
type: "RunEvidence"
id: "run-evidence/20260908t083545z-do-the-best-useful-work-availab/evidence-frontend-md-fixed"
run: "runs/20260908T083545Z-do-the-best-useful-work-available-in-this-reposi"
kind: "diff"
reference: "git diff -- FRONTEND.md"
summary: "Rewrote 3 FRONTEND.md sites (State Architecture ~line 556, Four tiers of state Tier 3 ~line 267, lib/ organisation table ~line 105) that cited a nonexistent completedItemsStore.svelte.ts and a fictional module-level-$state-in-.svelte.ts reactive singleton pattern with zero instances anywhere in web/src. Replaced with the real, grep-verified plain-.ts lazy-singleton pattern (queryClient.ts, duckdbSingleton.ts) and pointed shared-reactive-fetch needs at the already-documented TanStack Query section instead."
goal: "run-goals/20260908t083545z-do-the-best-useful-work-availab/goal-fix-frontend-md-singleton-drift"
---

# RunEvidence

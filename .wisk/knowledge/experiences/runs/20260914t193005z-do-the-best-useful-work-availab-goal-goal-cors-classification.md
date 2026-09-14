---
type: "RunGoal"
id: "run-goals/20260914t193005z-do-the-best-useful-work-availab/goal-cors-classification"
run: "runs/20260914T193005Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Fix issue #1482: DuckDBExplorer.svelte's dataset check reports a dataset 'ready' even when the Internet Archive download endpoint (unlike its metadata endpoint) sends no CORS header, so the browser's cross-origin read_parquet() Range fetch is permanently blocked -- yet the existing error classifier folds that failure into the generic transient 'unavailable' state and tells users to retry, which can never succeed."
rationale: "archive.org's /download endpoint lacking Access-Control-Allow-Origin was independently reconfirmed with curl in this session (a third client, after PR #1483's curl+urllib), against the currently-published djen-tjro-2026 item -- a real, live, credential-free production bug. #1471/#1472's remaining IA-publish work is already covered by open PR #1483 and blocked here by the same missing IA_ACCESS_KEY/IA_SECRET_KEY, so re-attempting it would duplicate unmerged work (see the handoff-disposition check); #1482 is genuinely actionable this round."
success_signal: "A RED test demonstrating the misclassification, a GREEN implementation that distinguishes a CORS-blocked dataset from a transient outage with an accurate non-retry message, the full web test suite (528+ tests) still green, ruff/eslint/astro-check clean, pushed to a branch with an open PR."
status: "active"
---

# RunGoal

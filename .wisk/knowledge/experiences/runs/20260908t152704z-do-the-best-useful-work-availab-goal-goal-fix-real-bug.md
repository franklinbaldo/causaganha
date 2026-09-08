---
goal: "Find and fix, via TDD, one real currently-live bug or a real gap in the CausaGanha sync engine or web frontend, driving the change through a merged PR."
id: "run-goals/20260908t152704z-do-the-best-useful-work-availab/goal-fix-real-bug"
kind: "task-advance"
rationale: "Issue queue (17 open) is fully pre-verified blocked (segmenter needs GPU/annotation; infra-hosting/credential-gated items; TSE 403). PR queue was empty except sibling-session PR #1322 (docs-only, behind main), which this round is separately bringing to green and merging as continuity work. This session-family's established fallback -- an Explore-agent codebase sweep -- has found a real, live, high-impact bug in every recent round (weekend-day miscounting, SQL NULL vs empty-string sentinel divergence, absent-status double counting), so it is dispatched again this round."
run: "runs/20260908T152704Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new test file/assertion exists that fails (RED) against the current code for a concrete, traced input, then passes (GREEN) after a minimal fix; full pytest/vitest suites plus ruff/eslint/astro-check stay green; a PR is opened, all CI checks succeed, and it is merged to main."
type: "RunGoal"
---

# RunGoal

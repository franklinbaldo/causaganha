---
goal: "Fix YearSummaryCards.svelte so its stat cards react to prop changes on a live instance instead of freezing at their first-mount values."
id: "run-goals/20260907t122956z-fa-a-o-melhor-avan-o-poss-vel-n/goal-year-summary-cards-reactivity"
kind: "task-advance"
rationale: "AnnualCoverageMonitor.svelte renders one persistent <YearSummaryCards> instance across year-button switches and force-refresh refetches (no {#key}), passing it complete/partial/low/missing as  props that change over the component's lifetime. YearSummaryCards computed its 'cards' array as a plain top-level const from the initial props (Svelte 5 flagged this at test time with 'state_referenced_locally' compiler warnings on all four props), so after the first render the visible summary cards never updated again — same reactivity-bug class as the AlertBanner fix in #1275 (const instead of $derived over a value derived from $props()). A scan of every other Svelte component destructuring $props() found no other live instance of this bug: the remaining three compiler warnings (TribunalCoverageExplorer, TribunalDetail, DateDetail) all seed $state once from static Astro-passed island props at mount, which is the correct, intentional pattern, not a bug."
run: "runs/20260907T122956Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
status: "carried_forward"
success_signal: "A rerender-based regression test (YearSummaryCards.reactivity.test.ts) fails RED before the fix — asserting the rendered .stat-value text after a Testing Library rerender with new complete/partial/low/missing — and passes GREEN once 'cards' is wrapped in $derived(...); the Svelte compiler's state_referenced_locally warnings for this file disappear; the full web vitest suite (490/490) and eslint (0 errors) stay green; a PR is opened and merged."
type: "RunGoal"
---

# RunGoal

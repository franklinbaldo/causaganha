---
type: "RunEvidence"
id: "run-evidence/20260907t122956z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-pr-1277-opened"
run: "runs/20260907T122956Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "execution"
reference: "https://github.com/franklinbaldo/causaganha/pull/1277"
summary: "PR #1277 (fix(web): make YearSummaryCards react to prop updates on a live instance) opened from commit abd440d on branch claude/exciting-mccarthy-wno5yu against main. Diff: web/src/components/YearSummaryCards.svelte wraps 'cards' in $derived(...); new file web/src/components/YearSummaryCards.reactivity.test.ts. Local verification before push: the new test failed RED against the pre-fix const version (readValues() stayed ['1','2','3','4'] after rerender with new props instead of updating to ['10','20','30','40']), then passed GREEN after the $derived fix; full web vitest suite 490/490 passing; eslint 0 errors."
goal: "run-goals/20260907t122956z-fa-a-o-melhor-avan-o-poss-vel-n/goal-year-summary-cards-reactivity"
---

# RunEvidence

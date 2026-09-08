---
goal: "Fix FRONTEND.md's Zod section and Known Gaps accessibility bullet so both describe real, grep-verified current code instead of a stale/fictional pattern."
id: "run-goals/20260908t092658z-do-the-best-useful-work-availab/goal-fix-frontend-md-zod-and-a11y-drift"
kind: "task-advance"
rationale: "Continuing this session-family's own established pattern (PRs #1307/#1309/#1311, all merged): FRONTEND.md has drifted from the real codebase in 3 consecutive prior rounds. The most recent RunOutcome's next_move named the doc's remaining untouched sections (Zod, DOMPurify, DuckDB, Testing, TypeScript, Known Gaps) as the best next candidate. Auditing them found two more real defects: the Zod section claims djen.ts holds 'the canonical patterns' and a z.preprocess example 'following the pattern in djen.ts', but djen.ts's own docstring says it dropped its ~200 lines of hand-written Zod schemas in favor of generated types (djen-zod.gen.ts) plus hand-written normalize* functions -- there is zero Zod and zero z.preprocess anywhere in web/src today (grep-verified). Separately, the Known Gaps section tells readers to read web/ACCESSIBILITY.md and web/ACCESSIBILITY_IMPROVEMENTS_NEEDED.md before touching any UI component -- neither file exists anywhere in the repo (confirmed via find + git log --all, no history at all), so the instruction is unfollowable and the real automated guard (svelteA11y.contract.test.ts, a compiler a11y_* warnings gate) goes undocumented."
run: "runs/20260908T092658Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "FRONTEND.md's Zod section names the real current boundary-validation sources (web/src/lib/data/contracts.ts for query contracts, web/src/lib/djen-zod.gen.ts/djenClient.ts for the generated DJEN schema) instead of the stale djen.ts claim, with every referenced file/function/line grep-verified to exist; the Known Gaps accessibility bullet names the real svelteA11y.contract.test.ts guard instead of two nonexistent files; and the full web suite (typecheck, lint, vitest) stays green after the edit, proving no code was broken by a docs-only change."
type: "RunGoal"
---

# RunGoal

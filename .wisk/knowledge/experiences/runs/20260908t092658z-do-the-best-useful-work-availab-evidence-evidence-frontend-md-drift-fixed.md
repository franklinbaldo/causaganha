---
type: "RunEvidence"
id: "run-evidence/20260908t092658z-do-the-best-useful-work-availab/evidence-frontend-md-drift-fixed"
run: "runs/20260908T092658Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "FRONTEND.md diff (Zod section lines ~460-530, Known Gaps accessibility bullet)"
summary: "Rewrote FRONTEND.md's Zod section to name web/src/lib/data/contracts.ts (hand-written schemas for .qmd query contracts, consumed via loadContract()'s schema.safeParse() at web/src/lib/data/index.ts:44) and web/src/lib/djen-zod.gen.ts (orval-generated from djen.yml, consumed via GetApiV1ComunicacaoResponse.safeParse(body) in djenClient.ts:437) as the real current boundary-validation sources, replacing the false claim that djen.ts holds 'the canonical patterns'. Replaced the fictional z.preprocess example (zero matches anywhere in web/src, confirmed by grep) with djen.ts's real normalizeMeio function as the actual hand-written coercion pattern this codebase uses instead. Rewrote the Known Gaps accessibility bullet to name the real automated guard (web/src/components/svelteA11y.contract.test.ts, a Svelte-compiler a11y_* warnings gate) instead of two nonexistent files (web/ACCESSIBILITY.md, web/ACCESSIBILITY_IMPROVEMENTS_NEEDED.md -- confirmed absent via find and git log --all with zero history)."
goal: "goal-fix-frontend-md-zod-and-a11y-drift"
---

# RunEvidence

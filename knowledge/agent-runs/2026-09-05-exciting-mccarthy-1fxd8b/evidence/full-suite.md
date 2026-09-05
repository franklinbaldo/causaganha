---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-full-suite"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "ci"
reference: "web vitest full suite, eslint, astro typecheck (baseline diff via git stash -u), ruff check, ruff format --check"
summary: "Full web vitest suite: 353/353 passing (up from 340 before this round). npm run lint: clean. npm run typecheck: 19 errors (up from a confirmed 16-error baseline via git stash -u against this branch's pre-round commit, 0 warnings, 3 hints unchanged) — the 3 new errors are all in the new ProcessoLookup.evidenceMatrix.test.ts and match the exact same pre-existing testing-library idiom (RenderResult.container typing under @testing-library/svelte) already present, unmodified, in ProcessoLookup.reference.test.ts — same pattern the qvwrkl round already established as an accepted non-regression. Python side untouched: ruff check and ruff format --check both pass. A codegen artifact (web/src/lib/djen-zod.gen.ts) drifted during `npm run pretypecheck`/`pretest` (orval/zod version-string cosmetic diff, no schema change) and was discarded, not committed."
---

# CI/gate evidence — full suite

vitest 353/353, eslint clean, typecheck delta +3 errors (known idiom, matches baseline pattern), 0 new warnings, hints unchanged at 3. ruff check/format clean.

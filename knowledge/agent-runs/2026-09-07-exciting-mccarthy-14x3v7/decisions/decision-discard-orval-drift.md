---
type: AgentDecision
id: "2026-09-07-exciting-mccarthy-14x3v7-decision-discard-orval-drift"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
goal_id: "2026-09-07-exciting-mccarthy-14x3v7-goal-djen-retry-after-floor"
question: "npm run typecheck (astro check) regenerated web/src/lib/djen-zod.gen.ts with a diff (orval version-comment change, zod.number() -> zod.int() for two id fields) as an unrelated side effect of running the prebuild codegen step in this environment. Should that regenerated file be included in this round's commit?"
choice: "Discard it via `git checkout -- web/src/lib/djen-zod.gen.ts`; commit only the intentional djenClient.ts fix and its test."
rationale: "The diff is generated-file drift from whatever orval version this environment's npm ci resolved, unrelated to the Retry-After defect this round is fixing — it changes zod.number() to zod.int() for two unrelated response id fields (PostApiV1LoginResponse.user.id, GetApiV1ComunicacaoTribunalResponseItem.id) and updates a version-string comment. Mixing an unrelated dependency-driven codegen regeneration into a scoped bugfix PR would widen its blast radius and risk masking the real diff during review, contradicting this project's own 'don't widen the PR on your own' rule. If the orval upgrade is intentional, it belongs in its own PR with its own review of the zod schema change's implications."
---

# Decisão: descartar drift de codegen do orval

`npm run typecheck` roda `codegen:djen-zod` (orval) como prebuild step; a versão do `orval` resolvida pelo `npm ci` deste ambiente difere da usada quando `djen-zod.gen.ts` foi commitado por último, produzindo um diff não relacionado ao fix desta rodada. Descartado com `git checkout --` para manter o PR restrito ao defeito real (`djenClient.ts`).

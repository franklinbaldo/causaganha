---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-diff"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
kind: "diff"
reference: "git diff --stat on this round's branch vs. commit dcda828"
summary: "6 files changed, 21 insertions(+), 11 deletions(-): .github/workflows/test.yml (+2, new 'Typecheck' step in the web job), web/src/components/__steps__/shared.ts (render wrapper's return type: `ReturnType<typeof _render>` → `RenderResult<Component<Props>>`, plus a matching Props constraint and doc comment explaining why), web/src/components/ProcessoLookup.{actions,evidenceMatrix,reference}.test.ts (each: `submit()`'s parameter type `ReturnType<typeof render>` → `RenderResult<typeof ProcessoLookup>`, +1 named type import), web/src/lib/data/renderedContracts.integration.test.ts (`readdirSync` gains `encoding: 'utf8'`; the `frontendByOutput` Map gets an explicit `Map<string, {...}>` type argument). Zero production .svelte/.astro files touched; zero Python files touched. Generated file web/src/lib/djen-zod.gen.ts, regenerated incidentally by the typecheck codegen hook due to a pre-existing orval-version drift unrelated to this round, was reverted (see decision-scope-revert-unrelated-drift) and does not appear in this diff."
---

# Diff desta rodada

6 arquivos, todos anotação de tipo em teste + 1 novo passo de CI. Nenhum arquivo de produção Svelte/Astro/Python tocado.

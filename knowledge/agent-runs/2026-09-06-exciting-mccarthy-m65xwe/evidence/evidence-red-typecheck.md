---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-red-typecheck"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
kind: "test_red"
reference: "web/ $ npm run typecheck, captured before any fix (commit dcda828, this round's branch point)"
summary: "`npm run typecheck` (astro check) exits 1 with 19 errors across 3 files: 15 in web/src/components/ProcessoLookup.{actions,evidenceMatrix,reference}.test.ts and web/src/components/__steps__/shared.ts's downstream consumer EmptyStates.contract.test.ts (all from the same `ReturnType<typeof render>` root cause), plus 2 narrower ones in web/src/lib/data/renderedContracts.integration.test.ts (a `readdirSync({recursive:true})` string/Buffer ambiguity and a Map keyed by a literal-union type queried with a wider string). Confirms the count round yigsua's evidence had logged in passing ('astro check: identical 19 pre-existing errors, no new ones') without investigating cause."
---

# RED: 19 erros de typecheck antes da correção

`npm run typecheck` falha com exit 1 e 19 erros, todos em arquivos de teste, confirmando o número já citado (sem investigação) por uma rodada anterior.

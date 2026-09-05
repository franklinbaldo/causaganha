---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-typecheck-baseline"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
kind: "diff"
reference: "cd web && npm run typecheck, compared via git stash -u against commit 248a7c5 (this round's commit_at_start) and again with this round's diff applied"
summary: "Baseline (git stash -u, all changes and new files removed): 16 errors, 0 warnings, 0 hints — identical to the count the immediately preceding round (2026-09-05-exciting-mccarthy-9xpeua) documented for its own PR #1148. With this round's diff restored: still 16 errors, 0 warnings, 3 hints — the 3 hints are 'await has no effect' on the same testing-library RenderResult.click() idiom already used by the pre-existing ProcessoLookup.reference.test.ts, in this round's two new test files. No new type error was introduced. A stray unrelated diff in web/src/lib/djen-zod.gen.ts (an orval-version string and zod.number()->zod.int() codegen drift, reproduced by every typecheck run in this sandbox due to a locally-installed orval version differing from the one that generated the committed file) was discarded via git checkout both times and is not part of this round's change."
---

# Evidência — baseline de typecheck preservado

`npm run typecheck` permanece em 16 erros pré-existentes antes e depois da mudança desta rodada; os únicos itens novos são 3 "hints" (não erros) no mesmo padrão já usado por testes existentes.

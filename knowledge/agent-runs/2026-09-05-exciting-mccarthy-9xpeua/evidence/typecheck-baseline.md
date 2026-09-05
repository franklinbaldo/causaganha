---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-9xpeua-evidence-typecheck-baseline"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
goal_id: "2026-09-05-exciting-mccarthy-9xpeua-goal-copy-reference-action"
kind: "diff"
reference: "npm run typecheck (astro check) on commit 6720d87 vs. on this round's working tree"
summary: "`npm run typecheck` reports the same 16 pre-existing ts(2345)/ts(2339) errors on the base commit (6720d87, before this round's changes, verified via `git stash`) and on this round's working tree — all in web/src/components/ProcessoLookup.actions.test.ts (a testing-library RenderResult generic-type mismatch already present in that file's existing 'submit' helper) and web/src/lib/data/renderedContracts.integration.test.ts (unrelated fs-buffer typing). This round's new ProcessoLookup.reference.test.ts mirrors the same pre-existing 'submit' helper pattern and inherits the same known type-mismatch, so the error count is unchanged (16 before, 16 after) — no new class of typecheck failure was introduced."
---

# Evidência: typecheck sem regressão

`astro check` já falhava com 16 erros antes desta rodada (confirmado via `git stash`); a rodada não altera essa contagem.

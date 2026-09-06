---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-8a9dnj-evidence-diff"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
goal_id: "2026-09-06-exciting-mccarthy-8a9dnj-goal-copy-link-coverage"
kind: "diff"
reference: "git diff web/src/components/TribunalCoverageExplorer.test.ts"
summary: "Added a `describe('copyQueryLink', ...)` block (3 tests + a local stubClipboard helper) to the end of the existing test file. No production code (TribunalCoverageExplorer.svelte) changed in the final diff — the mutation used to prove RED (evidence-red-mutation) was reverted before this diff was taken. Test-only change, additive to the existing 7 tests, same file/style conventions as the rest of the suite (render/screen/fireEvent/waitFor from @testing-library/svelte, vi.fn() from vitest)."
---

# Diff: apenas testes, produção intocada

Bloco `describe('copyQueryLink', ...)` acrescentado ao final do arquivo de teste existente; nenhuma mudança de produção no diff final (a mutação usada para provar RED foi revertida antes deste diff).

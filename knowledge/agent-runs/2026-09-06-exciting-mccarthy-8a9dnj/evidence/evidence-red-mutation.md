---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-8a9dnj-evidence-red-mutation"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
goal_id: "2026-09-06-exciting-mccarthy-8a9dnj-goal-copy-link-coverage"
kind: "test_red"
reference: "npx vitest run src/components/TribunalCoverageExplorer.test.ts, with production TribunalCoverageExplorer.svelte's copyQueryLink temporarily mutated (navigator.clipboard.writeText(window.location.href) -> navigator.clipboard.writeText(''))"
summary: "Because copyQueryLink already existed and worked correctly (shipped in #1213), the new tests passed immediately against the unmodified implementation — no naturally-occurring RED phase. To prove the new tests are not vacuous, deliberately mutated the implementation to copy an empty string instead of the real URL, reran the suite: 1 failed, 9 passed. The failing test ('copies the current page URL, including the drilldown query, and confirms success') failed with `AssertionError: expected '' to contain '/stats'`, exactly on the assertion checking the copied URL's content — confirming the test genuinely exercises copyQueryLink's URL-building behavior rather than passing by construction. The mutation was reverted immediately after (diff confirmed clean against the pre-mutation file)."
---

# RED: mutação deliberada prova que o teste não é vazio

`copyQueryLink` já existia e funcionava, então não havia uma fase RED natural. Mutei deliberadamente a implementação (copiar string vazia em vez da URL real) e confirmei que exatamente o teste que afirma o conteúdo da URL copiada falha (`expected '' to contain '/stats'`), depois revertive a mutação.

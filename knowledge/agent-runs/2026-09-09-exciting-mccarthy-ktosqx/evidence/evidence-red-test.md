---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ktosqx-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-ktosqx"
goal_id: "2026-09-09-exciting-mccarthy-ktosqx-goal-datedetail-page-probe-cap"
kind: "test_red"
reference: "web/src/components/DateDetail.pagination.test.ts::discovers all 35 pages, not just the first 30"
summary: "Ran `npx vitest run src/components/DateDetail.pagination.test.ts` against the unmodified DateDetail.svelte, with global.fetch mocked so that JSON page shards 1..35 all exist. Failed exactly as predicted: `screen.getByText('35 pág.')` never found -- the rendered DOM instead showed '30 pág.' in the header and a load-more button reading 'Página 2 de 30', confirming the fixed 30-item probe array silently caps discovery even when more pages genuinely exist and are reachable via HTTP."
---

# Evidência RED

```
TestingLibraryElementError: Unable to find an element with the text: 35 pág.. This could be because
the text is broken up by multiple elements. In this case, you can provide a function for your text
matcher to make your matcher more flexible.
...
<small class="meta-text" data-tone="muted">
  30 pág.
</small>
...
<button aria-busy="false" class="secondary" type="button">
  Página 2 de 30
</button>
```

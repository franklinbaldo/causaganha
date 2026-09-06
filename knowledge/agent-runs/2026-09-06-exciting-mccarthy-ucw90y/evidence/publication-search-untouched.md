---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-publication-search-untouched"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "diff"
reference: "web/src/components/PublicationSearch.svelte (main d2a4530 vs. reboot/cobogo-web 385970171515f6f33e42a4ec6083b895c93170ea)"
summary: "`git diff d2a4530..origin/reboot/cobogo-web -- web/src/components/PublicationSearch.svelte` returns zero lines. Same argument as ProcessoLookup: the empty/error distinction (point 2 of the owner's review request) cannot have regressed because the file implementing it is unchanged; only web/src/pages/publicacoes/index.astro (the Astro shell) was rewritten."
---

# Evidência — `PublicationSearch.svelte` intocado pela PR #1169

Diff vazio — o contrato `empty` vs `error`/indisponibilidade não foi tocado.

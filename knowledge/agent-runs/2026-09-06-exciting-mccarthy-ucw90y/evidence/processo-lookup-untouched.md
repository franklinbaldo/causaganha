---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-processo-lookup-untouched"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "diff"
reference: "web/src/components/ProcessoLookup.svelte (main d2a4530 vs. reboot/cobogo-web 385970171515f6f33e42a4ec6083b895c93170ea)"
summary: "`git diff d2a4530..origin/reboot/cobogo-web -- web/src/components/ProcessoLookup.svelte` returns zero lines. The component implementing the not_found/source_unavailable state machine is byte-identical between main and the PR head; only the surrounding Astro shell (web/src/pages/processo.astro) changed. This proves point 1 of the owner's requested review (ProcessoLookup contract preserved) by construction rather than by inspection of behavior."
---

# Evidência — `ProcessoLookup.svelte` intocado pela PR #1169

Diff vazio entre `main` e o head da PR para este arquivo — o contrato de estados (`not_found` vs `source_unavailable`) não pôde ter sido alterado porque o arquivo não mudou.

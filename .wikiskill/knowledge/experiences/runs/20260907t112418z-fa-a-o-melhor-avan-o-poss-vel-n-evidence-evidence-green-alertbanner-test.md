---
type: "RunEvidence"
id: "run-evidence/20260907t112418z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-green-alertbanner-test"
run: "runs/20260907T112418Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "execution"
reference: "local: cd web && npx vitest run src/components/AlertBanner.reactivity.test.ts (depois de trocar 'const isLive = ...' por 'const isLive = $derived(...)' em AlertBanner.svelte)"
summary: "GREEN confirmado: os 2 testes passam (2 passed). role agora atualiza de 'note' para 'alert' e vice-versa apos rerender com novas props level/live, sem recriar a instancia do componente. Diff minimo: uma linha (const -> $derived) em web/src/components/AlertBanner.svelte."
goal: "goal-fix-alertbanner-reactivity"
---

# RunEvidence

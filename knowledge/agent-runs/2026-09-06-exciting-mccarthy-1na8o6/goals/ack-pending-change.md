---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-1na8o6-goal-ack-pending-change"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
goal: "Stop /minhas-consultas from silently forgetting a detected 'mudou' verdict on the next automatic check, and give the user an explicit way to acknowledge it, closing issue #1232."
rationale: "#1132/#1133's whole value proposition is continuity: a change warning that can vanish just because the user reopened the page (which itself triggers another automatic checkForChanges()) is worse than no warning at all, because it teaches the user the warning is unreliable. #1232, filed by the repo owner 8 minutes before this round started and marked READY, is the only open issue with no external blocker — every other open issue is already recorded in knowledge/backlog/ as blocked (credentials, GPU/annotation work, or a product/infra decision). This is a small, local, TDD-friendly web slice with concrete acceptance criteria, matching this round's mandate to prioritize real, deliverable product advancement."
success_signal: "web/src/components/SavedConsultations.svelte only advances the stored baseline (consultationSnapshotStore) automatically on 'sem_historico' or 'sem_mudanca' verdicts; a 'mudou' verdict is held pending and survives an unmount/remount (simulating a reload) without a second automatic check silently reverting it to 'sem_mudanca'; a 'nao_comparavel' verdict (source outage) also never advances the baseline, so a real change is still caught once the source recovers; a new 'Marcar como visto' button, styled with the same outline/secondary class already used by the component's Renomear/Remover actions, appears only while a change is pending, is keyboard-reachable and activatable, and turns the verdict into 'sem_mudanca' (surviving a further reload) when clicked; removing a saved consultation still discards its pending state along with its snapshot. New Vitest tests in SavedConsultations.changeTracking.test.ts fail RED before the fix (proving the two-reload and outage-corruption bugs are real) and pass GREEN after; the full Python suite (ruff check, ruff format --check, pytest -q) and the full web suite (npm run lint, npm run typecheck, npm run test) stay green; a PR is opened and driven toward a mergeable, green state."
status: "achieved"
---

# Goal: reconhecimento explícito de mudança pendente em /minhas-consultas (#1232)

Separar "verificar" de "avançar a referência": um veredito `mudou` fica pendente até um "Marcar como visto" explícito, e uma indisponibilidade de fonte nunca corrompe a baseline — fechando #1232.

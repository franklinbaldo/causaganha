---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-488tov-decision-existing-wins-on-merge-collision"
run_id: "2026-09-06-exciting-mccarthy-488tov"
goal_id: "2026-09-06-exciting-mccarthy-488tov-goal-export-import-saved-consultations"
question: "When an imported item's canonical id already exists in local storage, which side wins — the existing local item or the imported one?"
choice: "The existing local item wins unconditionally (label and savedAt untouched); only ids absent from local storage are added from the import."
rationale: "Issue #1235's acceptance criteria call for 'deduplicar por identidade canônica já usada pelo storage, preservando rótulo existente de forma previsível' — 'preserving the existing label' is explicit. An import is framed throughout the issue as a restore/merge safety net (recovering a lost list, moving to a new browser), not a way to overwrite what the user already renamed or is actively using in the current browser. Existing-wins is also the simpler, more predictable rule to explain in the UI copy and to test (no field-by-field conflict resolution, no timestamp comparison needed), and it composes with re-importing the same backup file repeatedly being a safe no-op (tested in savedConsultationsBackup.test.ts's idempotency case)."
---

# Decisão: regra de merge

Em colisão de `id`, o item local existente vence integralmente; a importação só adiciona itens com `id` que ainda não existem localmente. Testado em `mergeSavedConsultations` (round-trip, colisão preservando rótulo local, idempotência, merge vazio).

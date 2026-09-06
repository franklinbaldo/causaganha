---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-red-green-snapshot-store"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
kind: "test_red"
reference: "web/src/lib/consultationSnapshotStore.test.ts written before consultationSnapshotStore.ts existed, then implemented; `npx vitest run consultationSnapshotStore` (web/) before and after"
summary: "RED: same import-resolution failure pattern as the pure module (0 tests ran, 'Failed to resolve import') with the storage test file present but consultationSnapshotStore.ts absent. GREEN after implementing get/save/removeConsultationSnapshot on top of a namespaced localStorage key (causaganha:consultation-snapshots:v1): all 5 cases passed — null for an unknown id, round-trip, independence between two different consultation ids, removal without touching others, and tolerance of a corrupted (non-JSON) value already at the storage key (returns null instead of throwing, and a subsequent save still succeeds)."
---

# RED→GREEN: consultationSnapshotStore.ts

Mesma sequência: `Failed to resolve import` com o módulo ausente → 5/5 testes verdes após a implementação, incluindo o caso de robustez (chave corrompida no localStorage).

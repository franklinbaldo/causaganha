---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-e9r0mj-check-vitest-red-mapping-parity"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
command: "npx vitest run src/lib/processoQueryPlanParity.test.ts (with mapDatajudRow's ultima_atualizacao temporarily reverted to toIsoDate)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-red-mapping-parity"
summary: "1 failed, 2 passed — the reintroduced mapping-layer parity test failed on datajud PRESENT with an ultimaAtualizacao mismatch ('2024-06-01' vs '2024-06-01T00:00:00'), reproducing PR #1125's original finding before this round's fix was re-applied."
---

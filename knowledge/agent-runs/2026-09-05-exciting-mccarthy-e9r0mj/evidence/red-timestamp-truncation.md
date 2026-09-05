---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-red-timestamp-truncation"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts, describe('mapDatajudRow'), it('preserves ultima_atualizacao time-of-day instead of truncating to a bare date (#1107)')"
summary: "Added a test feeding mapDatajudRow a raw ultima_atualizacao of '2024-06-01 14:23:05' (DuckDB's own space-separated VARCHAR-cast TIMESTAMP format) and asserting the view preserves the full instant '2024-06-01T14:23:05'. Ran `npx vitest run src/lib/processoCnj.test.ts -t mapDatajudRow` against the unmodified mapDatajudRow (still using toIsoDate for this field): the new test FAILED with 'expected 2024-06-01 to be 2024-06-01T14:23:05' — confirming the truncation drift diagnosed by #1107/PR #1125 is real and reproducible in a unit test, not just at the mapping-parity/integration level."
---

# RED: mapDatajudRow trunca ultima_atualizacao

Prova, a nível de teste unitário, o drift diagnosticado no comentário mais recente de #1107: `toIsoDate` descarta o componente de hora de `ultima_atualizacao`.

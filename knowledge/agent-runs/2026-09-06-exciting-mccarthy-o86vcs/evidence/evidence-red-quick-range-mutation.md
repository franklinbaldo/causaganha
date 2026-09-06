---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-o86vcs-evidence-red-quick-range-mutation"
run_id: "2026-09-06-exciting-mccarthy-o86vcs"
goal_id: "2026-09-06-exciting-mccarthy-o86vcs-goal-quick-range-coverage"
kind: "test_red"
reference: "web/src/components/TribunalCoverageExplorer.test.ts (describe: quick-range buttons); two deliberate mutations of web/src/components/TribunalCoverageExplorer.svelte's useRecentDays(), each reverted immediately after"
summary: "Wrote 6 new tests against useRecentDays (exact-day-count for 7/30/90, a UTC-midnight-boundary case under TZ=America/Los_Angeles, and an invalid/empty-end no-op case). All 6 passed immediately against the untouched implementation (it was already correct), so non-vacuousness was proven by mutation instead of by natural RED: (1) changing `- (days - 1)` to `- days` made exactly the 4 exact-date-count assertions fail (Expected 2026-02-23, Received 2026-02-22) while the other 11 tests stayed green; (2) keeping the UTC parse/arithmetic but formatting the result with local getters (getFullYear/getMonth/getDate) instead of toISOString() made exactly the TZ=America/Los_Angeles boundary test fail (Expected 2026-02-23, Received 2026-02-22) while the other 14 tests, including the same-timezone exact-count tests, stayed green — proving that specific test catches a parse/format timezone mismatch that the exact-count tests alone would miss. Both mutations were reverted via `cp` from a pre-edit backup and diff-verified byte-identical to the original before restoring."
---

# Evidência RED (por mutação)

A implementação de `useRecentDays` já estava correta, então a prova de não-vacuidade veio de duas mutações deliberadas e revertidas, cada uma derrubando exatamente o subconjunto de asserções que deveria: um off-by-one nos testes de contagem exata de dias, e uma formatação em hora local (mantendo o parse em UTC) apenas no teste de fronteira UTC/fuso horário.

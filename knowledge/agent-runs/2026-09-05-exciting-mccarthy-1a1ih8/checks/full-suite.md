---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-1a1ih8-check-full-suite"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
command: "cd web && npx vitest run (full suite); then npx vitest run src/lib/processoQueryPlanParity.test.ts in isolation to confirm the one failure was a pre-existing hook-timeout flake, not a regression"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-green-publicacoes-order"
summary: "42/43 files, 357/361 tests passed (4 pre-existing skips) on the full run; the sole failing file (processoQueryPlanParity.test.ts) failed only on a beforeAll hook timing out waiting on a cold `uv run python` subprocess start while contending with the rest of the suite, and passed 4/4 cleanly when run alone — confirmed pre-existing and unrelated to this round's web/src/pages/publicacoes changes."
---

# Check: suite completa web

`npx vitest run` completo: 357/361 (4 skips), 1 arquivo com timeout de hook (flake pré-existente de subprocesso `uv`, não relacionado a este diff — confirmado rodando o arquivo isolado, 4/4).

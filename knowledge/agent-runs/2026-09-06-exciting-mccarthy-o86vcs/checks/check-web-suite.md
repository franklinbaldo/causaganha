---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-o86vcs-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-o86vcs"
goal_id: "2026-09-06-exciting-mccarthy-o86vcs-goal-quick-range-coverage"
command: "cd web && npm test -- --run && npm run lint && npm run typecheck"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-o86vcs-evidence-green-quick-range"
summary: "58 test files / 456 tests passed; lint 0 errors; typecheck (astro check) 0 errors — all matching or improving on the pre-round baseline (451 tests)."
---

# Check: suíte web completa

Executado após o diff final (somente o arquivo de teste), com os artefatos gerados incidentalmente (`djen-zod.gen.ts`, `.claude/settings.local.json`) revertidos antes da checagem.

---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-iyujok-check-web-suite"
run_id: "2026-09-06-exciting-mccarthy-iyujok"
goal_id: "2026-09-06-exciting-mccarthy-iyujok-goal-mcpconfigcard-a11y"
command: "cd web && npm run lint && npm run typecheck && npm run test -- --run"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-iyujok-evidence-green-a11y-contract"
summary: "npm run lint: 0 errors, 43 pre-existing generated-file warnings (styled-system/*.d.ts unused-eslint-disable, unchanged baseline). npm run typecheck: 0 errors, 5 pre-existing hints (unchanged baseline). npm run test: 59 files / 452 tests passed, 0 failures, and the a11y_no_noninteractive_tabindex compiler warning that was present in the baseline run's stderr is gone from this run's output."
---

# Check: suíte web completa

`npm run lint`/`typecheck`/`test` rodados de ponta a ponta após a correção: 0 erros em lint e typecheck (mesmo baseline de warnings pré-existentes), 452/452 testes passando, warning de acessibilidade ausente do stderr.

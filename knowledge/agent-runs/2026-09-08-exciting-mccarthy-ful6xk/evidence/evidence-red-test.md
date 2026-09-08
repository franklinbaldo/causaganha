---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-ful6xk-evidence-red-test"
run_id: "2026-09-08-exciting-mccarthy-ful6xk"
goal_id: "2026-09-08-exciting-mccarthy-ful6xk-goal-fix-tribunal-completion-formula"
kind: "test_red"
reference: "web/src/lib/coverageInsights.test.ts (new file), run via `npx vitest run src/lib/coverageInsights.test.ts` before the fix"
summary: "Wrote two tests against the pre-fix code. Both failed as predicted: test 1 (fully-resolved tribunal, expectedDays=100/absentCount=15/coverageSize=85, true completion 100%) got a spurious 'tribunal-anomaly' card with summary 'Completude estimada em 85.0%...' instead of no card; test 2 (genuinely low completion, expected 45.0%) got the card but with the wrong percentage '40.0%' baked into its message (dropping the 5 absent days from the numerator). This confirms the bug is real and user-visible in the exact conditions the Explore-agent finding predicted, not a false positive."
---

# Evidência RED

Dois testes escritos contra o código anterior à correção. Ambos falharam como previsto: cartão de anomalia falso para tribunal totalmente resolvido (85.0% ao invés de 100%), e percentual errado (40.0% ao invés de 45.0%) para um tribunal genuinamente com baixa completude.

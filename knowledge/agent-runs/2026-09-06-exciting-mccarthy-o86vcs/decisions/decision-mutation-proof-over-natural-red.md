---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-o86vcs-decision-mutation-proof-over-natural-red"
run_id: "2026-09-06-exciting-mccarthy-o86vcs"
goal_id: "2026-09-06-exciting-mccarthy-o86vcs-goal-quick-range-coverage"
question: "The new quick-range tests passed immediately against the untouched implementation (no natural RED, since useRecentDays' UTC-anchored math was already correct). Is that acceptable, or should the round manufacture a real bug to fix?"
choice: "Accept immediate GREEN as the correct outcome and prove the new tests are not vacuous via two separate, reverted, deliberate mutations of the production code, each targeted at a different failure mode (day-count off-by-one; UTC-parse/local-format mismatch at a timezone boundary), following the precedent round 8a9dnj set for the same situation (copyQueryLink coverage)."
rationale: "This round's goal was explicitly framed as 'add coverage, and fix the implementation only if a real bug surfaces' — inventing a fake bug to satisfy a literal RED-before-GREEN reading of TDD would misrepresent the state of the code and waste effort on a non-problem. Mutation testing gives the same guarantee TDD's RED phase is meant to give (the test can actually fail) without fabricating a defect that does not exist in main today. Using two distinct mutations, not one, was necessary because the first (off-by-one) left the timezone-boundary test still passing — confirming that test needed its own, different mutation to prove it was pulling its own weight rather than being redundant with the exact-count tests."
---

# Decisão: prova por mutação em vez de RED natural

Testes que já nascem verdes contra uma implementação correta não violam o espírito do TDD deste projeto desde que sua capacidade de falhar seja demonstrada por mutação — o que esta rodada fez duas vezes, uma por asserção-alvo.

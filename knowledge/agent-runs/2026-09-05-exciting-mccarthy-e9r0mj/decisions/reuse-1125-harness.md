---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-e9r0mj-decision-reuse-1125-harness"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
question: "Now that the DataJud timestamp drift is fixed, should this round design a new mapping-layer parity harness from scratch, or reuse the one PR #1125 already wrote (and correctly left unmerged, since it went RED against the real bug)?"
choice: "Reuse PR #1125's harness verbatim: extend scripts/processo_query_plan_compare.py with _python_mapped() (dispatching to the real _build_djen/_build_juris/_build_stj/_build_datajud) and add the corresponding 'per-source mapped domain views agree' test to web/src/lib/processoQueryPlanParity.test.ts, unchanged from the closed PR's diff."
rationale: "#1125 was not closed because its design was wrong — it was closed because it correctly caught a real drift and merging it would have hidden that failure or forced masking it in the test. Its harness (call the real Python _build_* functions, call the real Web map*Row functions, compare against the shared query_plan_fixtures.py fixture) is exactly what #1107's acceptance criteria ask for: exercising the actual production mapping code, not a reimplementation of it in the test. Rewriting it would risk silently changing what gets exercised; reusing it verbatim and now watching it go GREEN is the cleanest proof that this round's fix is what #1125 was waiting on, and directly closes the mapping-layer-parity gap #1107's comment thread flagged as the next step after the temporal-authority fix."
---

# Decisão: reaproveitar o harness da PR #1125

O harness de #1125 já era a implementação certa — só ficou vermelho porque encontrou um bug real. Reaproveitá-lo integralmente prova que a correção desta rodada é exatamente o que faltava.

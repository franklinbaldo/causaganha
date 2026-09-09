---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-nnysz7-decision-scope-tribunal-coverage-out"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
goal_id: "2026-09-09-exciting-mccarthy-nnysz7-goal-totals-coverage-pct-null-not-nan"
question: "tribunal_coverage.qmd's coverage_pct (line 19) has the identical unguarded 100.0 * COUNT(*) FILTER(...) / COUNT(*) pattern as totals.qmd -- should this round's fix extend to it too?"
choice: "No -- leave tribunal_coverage.qmd untouched, fixing only totals.qmd."
rationale: "tribunal_coverage.qmd's COUNT(*) is the denominator of a per-tribunal GROUP BY tribunal aggregate. A GROUP BY group only exists in the result set when at least one row produced it -- COUNT(*) can therefore never be 0 within an existing group, so the NaN failure mode totals.qmd has (a global aggregate with no GROUP BY, where COUNT(*) really can be 0 for an empty manifest) cannot occur here. Verified by reading the full SQL block (GROUP BY tribunal ORDER BY coverage_pct DESC, tribunal) and confirming no code path produces a zero-row group. Applying NULLIF there anyway would be defensive code for a scenario that provably cannot happen, which CLAUDE.md and this project's general instructions both discourage. Keeps the fix minimal and exactly scoped to the verified live bug."
---

# Decisão: não tocar tribunal_coverage.qmd

Mesmo padrão textual de `totals.qmd`, mas sem o mesmo risco: o denominador é `COUNT(*)` dentro de um `GROUP BY tribunal`, que nunca é zero para um grupo existente. Corrigir ali seria validação para um caso que não pode ocorrer -- fora do escopo desta correção.

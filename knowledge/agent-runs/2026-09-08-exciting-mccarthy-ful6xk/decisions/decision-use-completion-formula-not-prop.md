---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-ful6xk-decision-use-completion-formula-not-prop"
run_id: "2026-09-08-exciting-mccarthy-ful6xk"
goal_id: "2026-09-08-exciting-mccarthy-ful6xk-goal-fix-tribunal-completion-formula"
question: "To fix the anomaly-card threshold, should buildTribunalAttentionCards() (a) drop its own 'completion' computation entirely and just use the params.completionPct prop the caller already computes correctly, or (b) keep computing its own 'completion' locally but fix the formula to include absentCount?"
choice: "(b) — fix the local formula to (coverageSize + absentCount) / expectedDays * 100, keep params.completionPct only as the expectedDays<=0 fallback (unchanged)."
rationale: "TribunalDetail.svelte's completionPct is rounded to one decimal (Math.round(...*1000)/10) for display, while the anomaly card's summary message calls .toFixed(1) on its own 'completion' value for a second decimal-formatted string — reusing the pre-rounded prop would double-round and could subtly diverge from the exact percentage this function's own message states. Recomputing from the same two integer inputs (coverageSize, absentCount, expectedDays) the function already receives keeps buildTribunalAttentionCards a pure, self-contained function of its params (easier to unit-test in isolation, as this round's new coverageInsights.test.ts does) rather than making its correctness depend on the caller having rounded completionPct identically. The bug was never 'which value to use' — it was the formula itself dropping a term that exists in every other completion calculation in the same file's caller (TribunalDetail.svelte:113-115) and in summarizeCatalogDay (lines 33-39, which folds absent into its own total). Fixing the formula in place is the minimal, correct change; switching to consume completionPct verbatim would be a larger behavioral change (removing a parameter's only remaining live branch) for no added correctness."
---

# Decisão: corrigir a fórmula local, não delegar para completionPct

Optei por corrigir a fórmula de `completion` dentro da própria função (somando `absentCount`) em vez de simplesmente usar o `completionPct` já calculado pelo chamador. O `completionPct` do chamador já vem arredondado para exibição; usá-lo aqui duplicaria o arredondamento e acoplaria a correção da função ao arredondamento externo. Recalcular a partir dos mesmos parâmetros mantém a função pura e testável isoladamente, e alinha a fórmula à mesma lógica já usada em `TribunalDetail.svelte` e em `summarizeCatalogDay` no mesmo arquivo.

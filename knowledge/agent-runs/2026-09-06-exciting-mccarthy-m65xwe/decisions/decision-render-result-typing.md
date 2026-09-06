---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-m65xwe-decision-render-result-typing"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
question: "17 of the 19 typecheck errors share one root cause (a Svelte Testing Library render-result type annotated as `ReturnType<typeof render>`). Fix it by widening/casting each failing call site individually, or by fixing the shared type annotation pattern itself?"
choice: "Fixed the type annotation pattern at its two sources — web/src/components/__steps__/shared.ts's `render` wrapper return type and the three ProcessoLookup.*.test.ts files' local `submit()` parameter type — replacing `ReturnType<typeof render>` with the library's own `RenderResult<C>` generic type (letting its `Q extends Queries = typeof queries` default apply). Did not touch any call site inside the function bodies."
rationale: "`ReturnType<typeof render>` (or `typeof _render`) taken on an uninstantiated generic function drops the generic's own default type parameter, which is exactly what collapsed `getByText`/`getByLabelText`/etc. to an incompatible union or index-signature type. Casting or `as`-ing each individual call site would have suppressed the 19 errors without removing the underlying bad pattern, leaving it ready to reproduce in the next new test file that copies the same `ReturnType<typeof render>` idiom. Fixing the two declaration sites removes the pattern itself, is strictly less code (2 files + 3 one-line signature changes vs. ~15 scattered casts), and needed zero changes inside any test body — all 15 downstream call-site errors disappeared once the parameter/return type was corrected, confirming the diagnosis was the true root cause rather than a coincidental fix."
---

# Decisão: corrigir a anotação de tipo na origem, não em cada call site

`ReturnType<typeof render>` descarta o valor-padrão do parâmetro genérico `Q` da própria função `render`. Corrigir a assinatura em `shared.ts` e nos três `submit()` locais elimina a causa raiz sem tocar o corpo de nenhum teste.

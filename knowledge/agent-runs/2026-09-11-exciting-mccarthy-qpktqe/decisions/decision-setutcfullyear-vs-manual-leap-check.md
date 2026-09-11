---
type: AgentDecision
id: "2026-09-11-exciting-mccarthy-qpktqe-decision-setutcfullyear-vs-manual-leap-check"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
question: "How should isValidCalendarDate's year-pivot bug (Date.UTC misinterpreting years 0-99 as 1900+year) be fixed: swap the Date construction method, or replace the whole round-trip validation strategy with a hand-rolled calendar validator?"
choice: "Swap Date.UTC(year, month-1, day) for `new Date(0); asUtc.setUTCFullYear(year, month-1, day)`, keeping the existing round-trip-through-UTC-components validation strategy unchanged. Rejected writing a hand-rolled leap-year/month-length calendar validator instead."
rationale: "setUTCFullYear(yearValue, monthValue, dayValue) sets the year component directly with no ECMA-262 two-digit-year reinterpretation -- confirmed live in this sandbox (`node -e \"const d=new Date(0); d.setUTCFullYear(1,0,1); console.log(d.getUTCFullYear())\"` prints 1, vs. `Date.UTC(1,0,1)` producing 1901). It also keeps the exact same normalize-and-round-trip validation idiom the function already uses and its docstring already explains (out-of-range month/day/leap-day roll over to the next month/year, so the round-trip only matches for genuinely valid input) -- the fix is a one-line construction change, not a rewrite of the validation strategy. A hand-rolled leap-year check (is-divisible-by-4-except-century-unless-400, per-month day-count table) would duplicate logic the runtime already gets right and would need its own separate test coverage for the exact same edge cases (Feb 29 on leap/non-leap years, 30 vs. 31 day months) that the existing round-trip approach already covers for free once the year-pivot bug is gone."
---

# Decisão: setUTCFullYear em vez de recriar a validação de calendário

Trocado `Date.UTC(year, month-1, day)` por `setUTCFullYear` na função de prova de `isValidCalendarDate`, mantendo a estratégia de validação por round-trip já existente. `setUTCFullYear` não tem a regra legada de pivô de ano de dois dígitos do ECMA-262 (confirmado ao vivo no sandbox). Rejeitada a alternativa de escrever um validador de calendário manual (ano bissexto, dias por mês), que duplicaria lógica que o runtime já resolve corretamente e exigiria sua própria cobertura de teste para os mesmos casos de borda que o round-trip existente já cobre de graça.

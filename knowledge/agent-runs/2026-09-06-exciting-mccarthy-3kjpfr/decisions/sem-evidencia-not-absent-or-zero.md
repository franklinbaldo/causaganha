---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-3kjpfr-decision-sem-evidencia-not-absent-or-zero"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
goal_id: "2026-09-06-exciting-mccarthy-3kjpfr-goal-drilldown-cobertura-por-tribunal"
question: "How should buildDailyStates() classify a day inside the selected period that has no row at all in tribunal_calendar for that tribunal — the exact case #1131's acceptance criteria call out ('ausência de linha no calendário não é apresentada como ausência confirmada nem falha')?"
choice: "A dedicated third status, sem_evidencia, distinct from uploaded and absent; summarizeDailyStates() excludes sem_evidencia days from the coveragePct denominator entirely (coveragePct is null, not 0, when zero days in the range are observed)."
rationale: "tribunal_calendar.qmd only emits rows where ia_status='uploaded' OR djen_status='absent' — a day can be missing from the contract for reasons unrelated to absence (not yet checked, checker error, day outside the tribunal's tracked window). Folding a missing day into 'absent' would fabricate a confirmed-absence claim the contract never made (directly violating CLAUDE.md's '403≠absent'/'don't trust absent from old runs' spirit for a different reason: absence of evidence isn't evidence of absence). Folding it into a 0% coveragePct would misrepresent a data gap as a coverage failure. Both are exactly the failure mode #1131 names as a risk ('voltar a expandir a taxonomia diária além do que o contrato prova' / caution against inventing pending/unknown per day) — the chosen design encodes the contract's actual epistemic state (three-way: proven-present, proven-absent, unproven) instead of collapsing it to the two states the contract happens to store rows for."
---

# Decisão: dia sem linha no contrato vira sem_evidencia, nunca absent nem 0%

`buildDailyStates()` classifica cada dia do período em `uploaded`/`absent`/`sem_evidencia`; `summarizeDailyStates()` retorna `coveragePct: null` quando nenhum dia do período tem evidência, em vez de fabricar 0%. Testado explicitamente em `tribunalCoverageDrilldown.test.ts`.

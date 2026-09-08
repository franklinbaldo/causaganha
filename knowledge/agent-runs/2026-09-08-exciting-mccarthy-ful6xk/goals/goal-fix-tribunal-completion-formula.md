---
type: AgentGoal
id: "2026-09-08-exciting-mccarthy-ful6xk-goal-fix-tribunal-completion-formula"
run_id: "2026-09-08-exciting-mccarthy-ful6xk"
goal: "Fix buildTribunalAttentionCards() in web/src/lib/coverageInsights.ts so its internal 'completion' calculation for the anomaly-card threshold matches the canonical formula already used by its only caller (TribunalDetail.svelte), by including absentCount (confirmed-absent days) instead of only coverageSize (collected days)."
rationale: "The function recomputes its own 'completion' percentage from coverageSize / expectedDays * 100, silently ignoring the absentCount parameter and the correctly-computed completionPct prop its caller already passes in. Since almost every tribunal has some legitimately-absent days (weekends, holidays — DJEN genuinely does not publish on those), this under-counts completion for essentially every tribunal with any data, and the code triggers a public-facing 'Destaque de anomalia' (anomaly) warning card whenever the resulting (wrong) completion falls below 90%, even for a tribunal that is fully caught up (actualMissingDays === 0)."
success_signal: "A test asserting a fully-resolved tribunal (missingDays=0, expectedDays=100, absentCount=15, coverageSize=85 — true completion 100%) produces NO 'tribunal-anomaly' card fails before the fix (RED, observed completion 85.0%) and passes after changing the formula to (coverageSize + absentCount) / expectedDays * 100 (GREEN); a second test confirms a genuinely low-completion tribunal (completion 45%) still triggers the card with the correct percentage in its message. Full web suite (vitest) stays green with one more test file/2 more tests than the pre-round baseline; lint and typecheck stay at 0 errors."
status: "achieved"
---

# Goal: corrigir fórmula de completude do cartão de anomalia por tribunal

`buildTribunalAttentionCards` recalcula "completion" internamente ignorando `absentCount`, ao contrário do `completionPct` já calculado corretamente pelo único chamador (`TribunalDetail.svelte`). Como praticamente todo tribunal tem dias legitimamente ausentes (fins de semana, feriados), isso sub-conta a completude e dispara um cartão público de "anomalia" mesmo para tribunais totalmente em dia. Corrigido para usar `(coverageSize + absentCount) / expectedDays * 100`, alinhado ao chamador.

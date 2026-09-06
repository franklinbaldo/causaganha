---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-1na8o6-decision-no-advance-on-outage"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
goal_id: "2026-09-06-exciting-mccarthy-1na8o6-goal-ack-pending-change"
question: "#1232's acceptance criteria say 'erro/fonte indisponível não modifica baseline'. The existing 'erro' catch-path already never saved. But compareConsultationSnapshots() also returns a distinct 'nao_comparavel' status (all previously-comparable sources became indisponível, but buscarProcesso itself succeeded — not an exception) — should the baseline advance for that status too, or only skip for the literal try/catch 'erro' case?"
choice: "Never advance the stored baseline on 'nao_comparavel' either, treating it the same as 'erro' and 'mudou' for baseline-advancement purposes (only 'sem_historico' and 'sem_mudanca' advance it automatically)."
rationale: "Before this fix, checkForChanges() called saveConsultationSnapshot(item.id, current) unconditionally, so a 'nao_comparavel' outage (djen indisponível) saved a snapshot whose djen field is null over a baseline that had real djen data. Traced the consequence in compareConsultationSnapshots(): once the baseline's djen is null, previousFields is null and the field is skipped without incrementing baselineSourceCount, so a later, fully successful check comparing against that corrupted baseline gets comparableSourceCount=0 AND baselineSourceCount=0 — which resolves to 'sem_mudanca' by the falsy branch, not 'nao_comparavel' — silently hiding a real subsequent change. This is a strictly worse failure mode than the 'mudou' bug named in the issue title, and is exactly the kind of thing the issue's own acceptance criterion 'erro/fonte indisponível não modifica baseline' rules out even though it names 'erro' rather than 'nao_comparavel' by name. Covered by a new test (RED before the fix, GREEN after) that reproduces this exact two-step scenario: a source outage followed by a genuine value change."
---

# Decisão: indisponibilidade de fonte (`nao_comparavel`) também nunca avança a baseline

Rastreamento mostrou que salvar a captura durante uma indisponibilidade corrompe a baseline com campos `null`, o que faz uma mudança real *subsequente* também desaparecer silenciosamente (a comparação null-vs-null resolve trivialmente para `sem_mudanca`). Tratado como o mesmo caso de `erro`/`mudou`: só `sem_historico` e `sem_mudanca` avançam a baseline automaticamente.

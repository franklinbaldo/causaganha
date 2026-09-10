---
type: AgentDecision
id: "2026-09-10-exciting-mccarthy-25og4b-decision-time-of-day-choice"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
question: "Make the STJ fixture's dataDecisao/dataPublicacao TIMESTAMP-typed at midnight (00:00:00, like the existing datajud fixture's ultima_atualizacao literals), or with a non-midnight time-of-day?"
choice: "Non-midnight time-of-day (e.g. TIMESTAMP '2024-05-01 14:23:05') for all three STJ rows' dataDecisao/dataPublicacao."
rationale: "A DATE -> TIMESTAMP type change alone (even at 00:00:00) is already sufficient to make ::DATE and ::VARCHAR diverge as strings ('2024-05-01' vs '2024-05-01 00:00:00'), so midnight would technically pass the new regression test. But a non-midnight time is strictly more faithful to what real STJ API data looks like (decisions are timestamped to the second, not just the day) and closes a second, related risk this round noticed while reading decisoes/search.py and reconcile_processos.py: both use TRY_CAST(\"dataDecisao\" AS DATE) defensively rather than assuming the real column is DATE-typed, which is consistent with the real upstream data carrying a time component. A midnight-only TIMESTAMP could tempt a future reader into believing time-of-day is always zero and reintroducing an assumption the fixture is meant to guard against. Chose distinct, plausible times per row (14:23:05, 09:00:00, 08:00:00, ...) rather than one shared time, so the fixture cannot accidentally rely on a single magic constant either."
---

# Decisão: horário não-meia-noite no fixture STJ

Trocar `DATE` por `TIMESTAMP` já bastaria tecnicamente (mesmo à meia-noite) para o teste de regressão passar, mas um horário não-meia-noite é mais fiel aos dados reais do STJ (decisões têm hora, não só dia) e evita que uma leitura futura do fixture assuma erroneamente hora-zero sempre. Horários distintos por linha, para não depender de uma única constante mágica.

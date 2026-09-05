---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-e9r0mj-decision-timestamp-string-normalization"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
question: "How should toIsoTimestamp() normalize DuckDB's VARCHAR-cast TIMESTAMP string ('YYYY-MM-DD HH:MM:SS', space-separated, no timezone) into an ISO-8601 form matching Python's datetime.isoformat()? The obvious approach mirrors toIsoDate() itself: `new Date(value).toISOString()`."
choice: "Do a plain string substitution (replace the single space between date and time with 'T') instead of reparsing through the JS `Date` constructor."
rationale: "`new Date('2024-06-01 14:23:05')` has no timezone marker, so JS parses it as LOCAL time and then `.toISOString()` converts it to UTC — silently shifting the instant by the browser/runtime's UTC offset (and potentially the calendar date, near midnight, in the exact way #1107's own investigation flagged as a latent bug in the existing toIsoDate() truncation). DataJud's ultima_atualizacao, like Python's naive datetime.isoformat(), has no explicit timezone; the only faithful transform that neither invents a timezone nor risks re-interpreting it is a syntactic one — same characters in, same characters out, only reformatted. This also keeps the function trivially total (no NaN-date edge case to special-case) and keeps the Web side from diverging from what Python literally received from the same DuckDB column."
---

# Decisão: normalização sintática, não via Date, para toIsoTimestamp

Reaproveitar `Date`/`toISOString()` (como `toIsoDate` já fazia) reintroduziria corrupção de fuso horário para um timestamp sem informação de fuso — a própria classe de bug que esta rodada corrige. Uma substituição de string simples (espaço → 'T') é suficiente e não interpreta nada que não esteja no valor original.

---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-vd5dfq-evidence-diff"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
kind: "diff"
reference: "web/src/lib/processoCnj.ts (+15/-1), web/src/lib/processoCnj.test.ts (+40/-1)"
summary: "processoCnj.ts: added BARE_ISO_DATE_RE and rewrote toIsoDate to short-circuit any naive 'YYYY-MM-DD[ T]HH:MM:SS' string (no zone marker) to its leading date digits, before falling through to the pre-existing Date-object/epoch/zoned-string handling; expanded the function's own docstring to explain why (mirrors toIsoTimestamp's existing rationale). processoCnj.test.ts: added 'does not shift the calendar day for a naive datetime string in a UTC+ timezone (#datajud-tz)' to the toIsoDate describe block, added 'does not roll dataAjuizamento back a day in a UTC+ timezone (#datajud-tz)' to the mapDatajudRow describe block, and removed the factually-incorrect comment on the pre-existing 'preserves ultima_atualizacao...' test claiming data_ajuizamento is a genuine DATE column."
---

# Diff desta rodada

`web/src/lib/processoCnj.ts`: `toIsoDate` extrai a data de uma string ingênua via regex antes de qualquer reinterpretação por `new Date()`. `web/src/lib/processoCnj.test.ts`: dois novos testes de regressão sob `TZ=Asia/Tokyo`, mais correção de um comentário de teste factualmente incorreto.

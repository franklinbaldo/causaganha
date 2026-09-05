---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-green-timestamp-fix"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
kind: "test_green"
reference: "web/src/lib/processoCnj.ts (new toIsoTimestamp(), mapDatajudRow now uses it for ultima_atualizacao instead of toIsoDate)"
summary: "Added toIsoTimestamp(value): normalizes DuckDB's VARCHAR-cast TIMESTAMP string (space-separated 'YYYY-MM-DD HH:MM:SS[.ffffff]') to ISO 'T'-separated form via a plain string regex substitution — deliberately NOT reparsing through `new Date(...)`, which would reinterpret a naive timestamp as local time and risk corrupting the instant near timezone boundaries (the same latent bug toIsoDate already carried, now avoided for this field). A bare 'YYYY-MM-DD' (DATE column) or null passes through unchanged, matching Python's date.isoformat()/None semantics for the same case. Re-ran the same 3 new tests (time-of-day preserved, bare-date unchanged, null unchanged) plus the pre-existing mapDatajudRow tests: all 5 pass."
---

# GREEN: toIsoTimestamp preserva o timestamp completo

`mapDatajudRow` agora usa `toIsoTimestamp()` só para `ultima_atualizacao` (a única coluna genuinamente `TIMESTAMP` do dossiê DataJud), preservando a mesma semântica temporal do `_iso()`/`isoformat()` do Python.

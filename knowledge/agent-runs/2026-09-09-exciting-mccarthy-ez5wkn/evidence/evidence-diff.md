---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-diff"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
kind: "diff"
reference: "scripts/render_queries.py, tests/test_render_queries.py"
summary: "git diff --stat: scripts/render_queries.py (+2/-2), tests/test_render_queries.py (+58). _DATAJUD_AGG_SQL's SELECT now emits regexp_replace(numero_processo, '[^0-9]', '', 'g') AS nr_processo (was numero_processo AS nr_processo) and its GROUP BY now groups by the normalized nr_processo alias (was the raw numero_processo column) -- the exact same regexp_replace-in-SELECT pattern already used by _DJEN_AGG_SQL, _JURIS_AGG_SQL, and _STJ_AGG_SQL. tests/test_render_queries.py gained one new test (test_processos_unificados_datajud_join_key_normalizes_punctuation) plus a short comment block explaining the sibling-inconsistency this closes -- the first test to exercise _register_processos_unificados/_UNIFICADOS_SQL/processos_unificados at all."
---

# Evidência: diff

Mudança de duas linhas em `_DATAJUD_AGG_SQL` (normalização da chave de join no SELECT e no GROUP BY, igualando o padrão já usado por `_DJEN_AGG_SQL`/`_JURIS_AGG_SQL`/`_STJ_AGG_SQL`) mais um teste novo cobrindo `processos_unificados` pela primeira vez.

---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-3-4-canary-alarm"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
kind: "diff"
reference: "scripts/canary_check.py:76,84,176-190; tests/test_canary_check.py:75-110; tests/test_render_queries.py:414-457"
summary: "#924 §3.4 claimed the declared 24h publication-to-archive SLO had no automated alarm despite pending_real already being computed. Live on main: `PENDING_REAL_THRESHOLD = 50` and `PENDING_REAL_MAX_AGE_HOURS_THRESHOLD = 24` are both defined and enforced in canary_check.py (lines 176-190 fail the canary when either is exceeded), with dedicated passing/failing unit tests (test_canary_check.py) and the underlying site_status.qmd field computation covered in test_render_queries.py (both tests reference '#924 §3.4' directly in their own comments). Already fully implemented."
---

# Evidência — #924 §3.4 (alarme do canário) já implementado

`PENDING_REAL_THRESHOLD` e `PENDING_REAL_MAX_AGE_HOURS_THRESHOLD` já existem e são testados, com testes que citam esta issue e subitem diretamente.

---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-589obm-evidence-red-backlog-985-category"
run_id: "2026-09-06-exciting-mccarthy-589obm"
goal_id: "2026-09-06-exciting-mccarthy-589obm-goal-fix-backlog-985-category"
kind: "test_red"
reference: "uv run pytest tests/knowledge/test_backlog.py -q, run against knowledge/backlog/issue-985.md before any edit to it"
summary: "New test test_backlog_item_985_reflects_its_actual_tse_network_blocker failed as expected: AssertionError: assert 'credentials' == 'network_access', confirming issue-985.md's frontmatter still carries the wrong category (and, per the same file's blocking_reason text checked in the same test, the wrong IAS3/Internet-Archive-credentials story) before the fix. The other 6 pre-existing tests in the file passed unchanged."
---

# Evidência RED: categoria errada da #985 no backlog

`assert 'credentials' == 'network_access'` — confirma que `issue-985.md` ainda carregava a categoria/motivo herdado do template de credenciais de IA antes da correção desta rodada.

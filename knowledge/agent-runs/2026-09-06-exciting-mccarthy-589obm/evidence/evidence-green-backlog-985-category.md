---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-589obm-evidence-green-backlog-985-category"
run_id: "2026-09-06-exciting-mccarthy-589obm"
goal_id: "2026-09-06-exciting-mccarthy-589obm-goal-fix-backlog-985-category"
kind: "test_green"
reference: "uv run pytest tests/knowledge/test_backlog.py -q, run after adding 'network_access' to knowledge/okf.schema.sql's BacklogItem.category CHECK and rewriting knowledge/backlog/issue-985.md"
summary: "All 7 tests in tests/knowledge/test_backlog.py pass, including the new test_backlog_item_985_reflects_its_actual_tse_network_blocker: issue-985.md's category is now 'network_access', and its blocking_reason names tse.jus.br while containing neither 'IAS3' nor 'Internet Archive'. No other backlog file's category or reasoning was touched."
---

# Evidência GREEN: backlog da #985 corrigido

`.......` (7 passed) em `tests/knowledge/test_backlog.py` após adicionar `network_access` ao schema e reescrever `issue-985.md` com o motivo real.

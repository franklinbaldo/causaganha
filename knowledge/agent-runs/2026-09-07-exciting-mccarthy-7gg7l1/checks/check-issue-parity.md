---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-7gg7l1-check-issue-parity"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
command: "mcp__github__list_issues(state=OPEN) issue numbers vs `ls knowledge/backlog/issue-*.md`"
result: "passed"
evidence_id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-issue-backlog-parity"
summary: "Exact 1:1 match, 17 issues both sides. No open issue is uncached; no cached issue has closed."
---

# Check: paridade issues abertas x backlog

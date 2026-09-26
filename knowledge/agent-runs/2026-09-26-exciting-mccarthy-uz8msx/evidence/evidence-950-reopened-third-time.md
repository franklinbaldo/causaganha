---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-uz8msx-evidence-950-reopened-third-time"
run_id: "2026-09-26-exciting-mccarthy-uz8msx"
goal_id: "2026-09-26-exciting-mccarthy-uz8msx-goal-950-reopen-safely"
kind: "issue"
reference: "https://github.com/franklinbaldo/causaganha/issues/950, https://github.com/franklinbaldo/causaganha/pull/1663"
summary: "PR #1663 (this round's own report/close-out PR) reclosed issue 950 the instant it merged, even though its title/body avoided writing a closing keyword directly next to the issue's hash-number as a live reference -- the PR body instead quoted, inside quotation marks, the literal problem phrase from PR #1661's title while explaining the bug. GitHub's closing-keyword scanner does not parse markdown quoting; it matched the quoted substring anyway and closed the issue again on merge (closed_at == merged_at for #1663, same signature as the first incident). Reopened a third time via issue_write; posted a follow-up comment that deliberately avoids reproducing the trigger phrase even inside quotes, referring to the issue by its bare number or full URL instead. knowledge/backlog/issue-950.md gained a second dated note with the corrected, stricter lesson: never write one of the closing-style words immediately followed by this issue's hash-number in any PR title/body/commit, not even to quote the bug being described. issue_read reconfirms state='open'/state_reason='reopened' after the third reopen."
---

# Evidência: issue 950 reaberta pela terceira vez -- mesmo padrão, disparado por citação entre aspas

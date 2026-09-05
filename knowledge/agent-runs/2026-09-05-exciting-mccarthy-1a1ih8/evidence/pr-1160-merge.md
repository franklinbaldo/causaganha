---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-pr-1160-merge"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1160, merged as commit 57cc03f onto main"
summary: "PR #1160 merged. Between this round's last push (1a1ba8b) and the merge, a separate automated process rebased this branch's exact diff (the /publicacoes reorder plus the underscore-prefixed order test, byte-identical to what this round authored) onto a newer main that had absorbed two unrelated PRs (#1162 segmenter cleanup, #1165 segmenter eval closure) merged in the interim, as commits 15e61f7 ('feat(web): rebase publicacoes hierarchy on current main') and dcccd18 ('test(web): preserve publicacoes search-first hierarchy') — the same pattern this round's own readings/issues.md noted from #1150/#1151. That rebase closed and reopened PR #1160 once (transient close/reopen events observed), re-ran CI clean on the rebased head, and it was merged as 57cc03f. This round's own knowledge/agent-runs/2026-09-05-exciting-mccarthy-1a1ih8/ report tree was not carried over by that external rebase (only the code diff was), so this evidence file and the corresponding run.md update are being added as a fresh follow-up commit on a freshly restarted branch (per this session's own branch-restart convention for an already-merged PR), restoring the full report tree from this round's original commits and recording the final merged outcome."
---

# Evidência: merge da PR #1160

PR #1160 mesclada como `57cc03f` em `main`. Um processo externo reautuou o mesmo diff (idêntico byte a byte) sobre um `main` mais novo (após #1162/#1165) e a PR foi verde e mesclada nesse head reautuado (`dcccd18`). Esta rodada restaura sua própria árvore de relatório OKF (removida pela reautuação externa, que preservou só o diff de código) e registra o desfecho final.

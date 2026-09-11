---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-codex-finding-1457"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-isovalidcalendardate-year-pivot"
kind: "review"
reference: "https://github.com/franklinbaldo/causaganha/pull/1457#issuecomment-5628995900"
summary: "Codex's automated Code Review on PR #1457 (the previous round's closing-report follow-up, which this round's PR-reading action pushed a merge-conflict-resolution commit to) flagged, among 5 findings, a P2 bug at web/src/lib/processoCnj.ts#L321 ('Preserve valid ISO years below 100'): 'For otherwise valid four-digit ISO inputs whose year is 0000-0099, Date.UTC applies its legacy 1900-year offset, so this round trip rejects them ... Construct the UTC date and then call setUTCFullYear(year) ... so all years accepted by the documented YYYY-MM-DD format remain valid.' Independently verified live in this sandbox before adopting as this round's goal (see reading-prs.md and goal-isovalidcalendardate-year-pivot.md): `node -e \"console.log(new Date(Date.UTC(1,0,1)).getUTCFullYear())\"` printed 1901, confirming the bug is real and reproducible, not a false positive. The other 4 findings on the same comment concern content not in PR #1457's own diff (already-merged AgentCheck/AgentRun narrative from PR #1456, plus the standing Wisk-vs-AgentRun disagreement already settled in prior rounds) -- disposition of all 5 recorded in a PR comment (issuecomment-5629042884) after #1457 was merged."
---

# Achado do Codex na PR #1457

Codex apontou um bug P2 real em `isValidCalendarDate` (pivô de ano legado do ECMA-262 para anos 0-99 via `Date.UTC`). Verificado de forma independente antes de virar goal desta rodada. Os outros 4 achados do mesmo comentário são sobre conteúdo fora do diff da PR #1457 (já mesclado via #1456); disposição registrada em comentário na PR após o merge.

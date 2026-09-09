---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-8esdwh-decision-close-stale-pr-1364"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
question: "PR #1364 (a round-closeout doc PR from a concurrent same-family session) is stale, dirty against current main, and its content is already merged via PR #1363. Merge it anyway to be safe, leave it open, or close it?"
choice: "Close #1364 without merging, with a comment naming #1363/b37e970 as the superseding merge."
rationale: "GitHub reports mergeable_state='dirty' -- it cannot merge cleanly regardless. Its two changed files (evidence-pr-1362-merged.md, run.md's result_state flip) are byte-for-byte already on main via #1363, which additionally has a checks/ file #1364 lacks -- so merging would add nothing and risks a bad three-way merge resolution on run.md. Leaving it open indefinitely would make it look like actionable backlog to every future round's PR-reading step, wasting re-investigation effort. Closing with an explanatory comment is safe (no code loss -- the branch/commits remain reachable) and keeps the PR queue honest."
---

# Decisão: fechar a PR #1364

PR de fechamento de rodada duplicada e obsoleta (corrida entre sessões concorrentes; a #1363 já mesclou o mesmo conteúdo). Fechada sem merge, com comentário explicando a substituição.

---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-j2t668-evidence-pr-merged"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
goal_id: "2026-09-16-exciting-mccarthy-j2t668-goal-djen-sample-batch15"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1570"
summary: "PR #1570 merged (squash) as commit 7dcfd2b. 11/11 CI checks green (CodeQL x4, GitGuardian, lint, archive-cors-proxy, validate, web, tests (tjro)), mergeable_state=clean, 0 open review threads. Session unsubscribed after merge."
---

# Evidencia: PR #1570 mesclada

PR #1570 ("feat(segmenter): ingest fifteenth real multi-tribunal batch
via Technique 1 (#1050)") mesclada via squash como commit `7dcfd2b`.
Todos os 11 checks de CI verdes no head final (`80eee20`, apos o merge
de `main` para resolver o `mergeable_state=behind` causado pelo commit
Wisk concorrente `c92cf7f`): CodeQL (4 linguagens), GitGuardian, lint,
archive-cors-proxy, validate, web, tests (tjro). Nenhum thread de review
aberto. Sessao desinscrita da PR apos a confirmacao do merge.

Durante o ciclo de CI, dois problemas reais e pequenos foram encontrados
e corrigidos no proprio PR: (1) `evidence_id: ""` em vez de `null` num
`AgentCheck` (OKF022), e (2) um arquivo de evidencia novo
(`segmenter-djen-sample-batch15-fix-nbsp.py`) que precisava de
`ruff format`. Ambos corrigidos por commits de acompanhamento antes do
merge, sem exigir nenhuma intervencao humana.

---
type: AgentEvidence
id: "2026-09-19-exciting-mccarthy-gbf44b-evidence-pr-1585-merged"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
goal_id: "2026-09-19-exciting-mccarthy-gbf44b-goal-djen-sample-batch22"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1585, merge commit e54a0b01c174dfa222803b4c61fd661c07a3fd2c"
summary: "PR #1585 merged by franklinbaldo at 2026-09-19T23:31:20Z (squash-merged onto main as e54a0b0). Final head (a4c78db) passed all 11/11 CI checks, including tests (tjro) at 15m19s -- confirming the timeout-minutes 15->25 fix resolved the two prior cancellations without masking a real defect."
---

# Evidencia: PR #1585 mesclada

`tests (tjro)` no head final (`a4c78db`, apos o fix de timeout) rodou
`Run ./.github/actions/run-tests` de 19:51:26 a 20:06:45 = ~15min19s --
acima do teto antigo de 15min (que teria cancelado de novo) e
confortavelmente dentro do novo teto de 25min. Isso confirma
empiricamente a decisao (`decision-bump-ci-test-timeout`): o tempo real
da suite ja ultrapassa o teto antigo, nao foi apenas uma variancia de
runner que um re-run resolveria. Os outros 10 checks (CodeQL, web,
archive-cors-proxy, lint, validate, Analyze x4, GitGuardian) passaram
normalmente. `mergeable_state` era `unstable` antes deste fix e a PR
foi mesclada logo apos a CI ficar verde -- sem review humano bloqueante
pendente (Codex Security Review ja havia completado sem achados antes
do fix de timeout).

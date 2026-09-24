---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-eb5f9r-evidence-pr-1598-merged"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
goal_id: "2026-09-24-exciting-mccarthy-eb5f9r-goal-unstick-continuity-prs"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1598"
summary: "PR #1598 (fix de performance O(n^2) em dedup.py) mesclada via mcp__github__merge_pull_request (squash) apos update_pull_request_branch trazer o head para f487151 (sincronizado com main) e o GitGuardian Security Checks fresco (13:33:33-13:33:35Z) satisfazer o required-status-check do ruleset. Commit 6d2ac9a em main. scripts/segmenter_governance_status.py, que travava >8min no corpus real de 191 documentos, agora e esperado rodar em ~1min (medido na propria PR)."
---

# Evidencia: PR #1598 mesclada

`mcp__github__merge_pull_request` (squash, expectedHeadSha=f487151a...)
retornou `{"sha":"6d2ac9aabb1cb97490a19ca4c68fa177410905b0","merged":
true}`. Confirma a hipotese registrada em `check-1598-1599-merge-
ruleset-blocker`: apos `update_pull_request_branch` disparar CI fresco
(incluindo um novo `GitGuardian Security Checks`), o merge que antes
falhava com 405 foi aceito sem alterar nada no codigo da PR.

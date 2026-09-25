---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-230b86-evidence-pr-1651-merged"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-datajud-merge"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1651"
summary: "PR #1651 (security(datajud): embed identity KV_METADATA in parquet exports, #1610 TM-04) mesclada via squash nesta rodada, sha 02a4c751d5f64de1aa23335ef19171cfb2c92a75. Antes do merge: 15/15 check runs com conclusion=success (CodeQL, GitGuardian, supply-chain, djen-proxy, archive-cors-proxy, web, tests (tjro), relay-cf, validate, lint, compare-product-surfaces, Analyze x4), mergeable_state=clean, review de seguranca do Codex completa sem findings bloqueantes, zero comentarios de revisao pendentes."
---

# Evidência: merge de #1651

`mcp__github__merge_pull_request` (squash, `expectedHeadSha` casando com
o head da PR) retornou `merged: true`, sha `02a4c75`. Confirma o fechamento
do lado de escrita+leitura de TM-04 para `datajud`.

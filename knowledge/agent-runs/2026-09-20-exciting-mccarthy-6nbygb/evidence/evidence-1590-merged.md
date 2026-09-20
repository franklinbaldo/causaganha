---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-6nbygb-evidence-1590-merged"
run_id: "2026-09-20-exciting-mccarthy-6nbygb"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1590"
summary: "PR #1590 (lote 24 real para #1050) squash-mesclada nesta rodada como dba8dcf861dd611dfde28ba2c16ee13db48014ab, apos reverificacao independente (worktree separado: ruff limpo, pytest -q tests/segmenter_dataset 100% verde, git diff --stat confirmando exatamente 5 pares document/annotation novos). Os 7 achados de review do Codex ja estavam resolvidos com correcoes verificadas contra o texto-fonte por uma sessao anterior (commit cbac93e). mcp__github__merge_pull_request(merge_method=squash, expectedHeadSha=4326a76...) retornou merged:true."
---

# Evidência: merge de PR #1590

`merge_pull_request` com `expectedHeadSha` travado no sha exato ja
reverificado (4326a76...), garantindo que nao houve nenhuma mudanca
entre a reverificacao e o merge. Resultado: `merged:true`, sha do commit
de squash `dba8dcf861dd611dfde28ba2c16ee13db48014ab`.

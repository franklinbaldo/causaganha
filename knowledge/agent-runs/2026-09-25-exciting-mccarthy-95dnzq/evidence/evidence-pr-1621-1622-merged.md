---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-95dnzq-evidence-pr-1621-1622-merged"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1621 (sha 41a0815, fecha #1611/TM-05) e https://github.com/franklinbaldo/causaganha/pull/1622 (sha de100dad, fecha parte de #1610/TM-03) -- ambas de sessoes concorrentes desta mesma janela"
summary: "Ambas verificadas com mergeable_state=clean e todos os check runs 'success' antes do merge (11/11 para #1621, 10/10 para #1622) via mcp__github__pull_request_read. #1621 mesclada primeiro (squash). A tentativa de mesclar #1622 logo depois falhou com 405 ('GitGuardian Security Checks' exigido nao reportado contra o main ja avancado por #1621) -- sincronizada via mcp__github__update_pull_request_branch, CI rerodou 10/10 verde no novo head (b274b4d), mesclada em seguida (squash). Nenhuma das duas e trabalho desta sessao; landing de continuidade antes do trabalho de dominio, mesmo padrao ja seguido por rodadas anteriores desta janela (p973xb, khpkk2, 1c8jcc)."
---

# Evidencia: PRs #1621 e #1622 mescladas no inicio da rodada

Landing de trabalho pronto de duas sessoes concorrentes antes de
selecionar o trabalho principal desta rodada. Ver `reading-prs` para o
estado verificado ao vivo antes de cada merge.

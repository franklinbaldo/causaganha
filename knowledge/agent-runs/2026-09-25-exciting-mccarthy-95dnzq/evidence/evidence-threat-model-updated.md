---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-95dnzq-evidence-threat-model-updated"
run_id: "2026-09-25-exciting-mccarthy-95dnzq"
goal_id: "2026-09-25-exciting-mccarthy-95dnzq-goal-djen-proxy-egress-policy"
kind: "diff"
reference: "docs/SECURITY_THREAT_MODEL.md, linha TM-02 e data de atualizacao do topo"
summary: "TM-02 (Sec.3) atualizada para refletir o estado real pos-rodada: djen_proxy.go agora listado como corrigido (so GET, so /api/, com deployment/djen_proxy_test.go e a job de CI djen-proxy como gate automatizado), enquanto o relay Python e o relay Cloudflare permanecem com a lacuna de metodo amplo e ausencia de stripping de Authorization/Cookie ja documentada explicitamente como pendente -- para que a proxima rodada nao precise reler o codigo dos 3 arquivos para saber o que ja foi feito. #1609 nao foi fechada (issue continua com criterio de conclusao parcial)."
---

# Evidencia: threat model atualizado para refletir o estado parcial real

`docs/SECURITY_THREAT_MODEL.md` documenta continuidade entre rodadas
sobre a mesma issue heterogenea -- a atualizacao evita que uma rodada
futura precise rederivar do zero o que ja foi corrigido em
`djen_proxy.go` versus o que ainda falta nos dois relays.

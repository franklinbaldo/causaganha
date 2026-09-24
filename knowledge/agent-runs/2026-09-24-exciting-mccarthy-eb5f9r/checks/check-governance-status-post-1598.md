---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-eb5f9r-check-governance-status-post-1598"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
goal_id: "2026-09-24-exciting-mccarthy-eb5f9r-goal-unstick-continuity-prs"
command: "time uv run python scripts/segmenter_governance_status.py (branch local ressincronizada com main pos-merge de #1598, commit 6d2ac9a)"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-eb5f9r-evidence-pr-1598-merged"
summary: "50.425s de wall-clock no corpus real de 191 documentos (antes: >8min travado, confirmado pela propria PR #1598). document_count=191, annotation_count=244, val_ceiling=test_ceiling=29, meets_rfc_0012_split_floor=false, corpus_scale_blocks_floor=true -- consistente com o estado esperado pos-lote25, confirma que o fix de performance nao alterou nenhum numero de governanca, apenas o tempo de execucao."
---

# Check: governance-status pos-merge de #1598

Rodado ao vivo apos ressincronizar a branch local com `origin/main`
(commit `6d2ac9a`, que inclui o fix de `dedup.py` de #1598). Tempo caiu
de >8 minutos travado (baseline documentado na propria PR #1598, medido
por uma sessao anterior) para 50.425s, sem alterar nenhum numero de
governanca (`document_count=191`, `annotation_count=244`,
`val_ceiling=test_ceiling=29`). Confirma que o proximo lote de dados de
#1050 (batch26) pode usar `segmenter_governance_status.py` como
pre-checagem padrao novamente, sem risco de travar a rodada.

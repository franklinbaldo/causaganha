---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-x3954c-check-governance-status-runtime"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
command: "time uv run python scripts/segmenter_governance_status.py"
result: "passed"
evidence_id: "2026-09-20-exciting-mccarthy-x3954c-evidence-runtime-measurement"
summary: "Rodado sobre o corpus real (data/segmenter, 191 documentos) apos a correcao: 1m6.470s de tempo real, retornando document_count=191/annotation_count=244/val_ceiling=test_ceiling=29 -- identico ao que a PR #1597 ja documentava para o estado pos-lote-25. Antes da correcao, a mesma chamada nao completou em 8+ minutos (processo preso a 99.9% CPU, morto manualmente apos confirmar via amostragem que o custo projetado da etapa de dedup sozinha era de ~493s)."
---

# Check: runtime do script de governança pós-fix

```
$ time uv run python scripts/segmenter_governance_status.py
{
  "document_count": 191,
  "annotation_count": 244,
  "review_count": 31,
  "train_eligible_count": 191,
  "evaluation_eligible_count": 31,
  "blocked_on_reviews": false,
  "val_count": 29,
  "test_count": 2,
  "val_ceiling_at_full_adjudication": 29,
  "test_ceiling_at_full_adjudication": 29,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": true
}

real	1m6.470s
```

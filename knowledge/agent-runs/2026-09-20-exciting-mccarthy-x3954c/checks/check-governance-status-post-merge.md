---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-x3954c-check-governance-status-post-merge"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
command: "time uv run python scripts/segmenter_governance_status.py (rodado sobre origin/main apos o merge de PR #1598)"
result: "passed"
evidence_id: "2026-09-20-exciting-mccarthy-x3954c-evidence-pr-1598-merged"
summary: "Reconfirmado ao vivo sobre main pos-merge (commit 6d2ac9a): 43.430s de tempo real (ainda rapido, nao regrediu), document_count=191, annotation_count=244, val_ceiling=test_ceiling=29 -- numeros inalterados desde a PR #1597 (correcao de revisao, sem novos documentos). Piso RFC 0012 Sec 5 item 4 (>=30 val, >=30 test) ainda nao alcancavel; falta crescer o corpus (#1050) para uma rodada futura."
---

# Check: governance status pós-merge, sobre main

```
$ time uv run python scripts/segmenter_governance_status.py
{
  "document_count": 191,
  "annotation_count": 244,
  "review_count": 31,
  "val_count": 29,
  "test_count": 2,
  "val_ceiling_at_full_adjudication": 29,
  "test_ceiling_at_full_adjudication": 29,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": true
}
real	0m43.430s
```

Confirma que a correção desta rodada continua funcionando corretamente
e rápido sobre o `main` real, pós-merge da própria PR #1598 e da PR
concorrente #1597.

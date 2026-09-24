---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-khpkk2-check-governance-status-still-fast"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
goal_id: "2026-09-24-exciting-mccarthy-khpkk2-goal-land-batch26-resolve-stale-1600"
command: "time uv run python scripts/segmenter_governance_status.py --store data/segmenter"
result: "passed"
summary: "Reconfirmado ao vivo (antes do merge de #1603) que o fix de performance de #1598 continua valido no corpus atual de 191 documentos: 0m57.199s (real), document_count=191, annotation_count=244, val_ceiling=test_ceiling=29 -- consistente com a medicao de #1602 (~1min). Nenhuma regressao de performance introduzida pelos merges desta manha."
---

# Check: governance status ainda rapido

```
$ time uv run python scripts/segmenter_governance_status.py --store data/segmenter
{
  "document_count": 191,
  "annotation_count": 244,
  "val_ceiling_at_full_adjudication": 29,
  "test_ceiling_at_full_adjudication": 29,
  ...
}
real  0m57.199s
```

Confirma que o gargalo O(n^2) corrigido em `#1598` continua corrigido
apos os merges desta manha (`#1597`/`#1598`/`#1599`/`#1602`), antes de
`#1603` (lote 26) ser mesclado.

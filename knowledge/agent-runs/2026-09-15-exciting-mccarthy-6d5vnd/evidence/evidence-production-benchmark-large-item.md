---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6d5vnd-evidence-production-benchmark-large-item"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
kind: "runtime"
reference: "docs/planning/evidence/bloom-filter-a1c-production.json (scripts/benchmarks/bloom_filter_production.py contra djen-tjro-2026/comunicacoes.parquet real, 1.041.723 linhas)"
summary: "CNJ mais repetido (70058285020258220014, 64 ocorrências) reescrito sob os dois layouts candidatos com WRITE_BLOOM_FILTER true e ROW_GROUP_SIZE 122880: ordenação cnj_first (produção) e date_first ambas ficam 100% PLAIN (0/9 row groups com bloom filter) -- a repetição real por CNJ é baixa demais para dictionary-encoding num grupo de ~115K linhas, confirmando o caso 'quase único' já previsto pela matriz sintética. Mas cnj_first ainda poda o point-lookup a 1 row group via min/max stats sozinho (mesmo resultado que A1b já havia medido), enquanto date_first toca todos os 9. Decisão resultante: índice covering aditivo não é necessário."
---

# Evidência: benchmark real (item grande, djen-tjro-2026)

```json
{
  "sample_cnj": "70058285020258220014",
  "sample_cnj_occurrences": 64,
  "total_rows": 1041723,
  "measurements": [
    {"ordering": "cnj_first", "row_group_count": 9, "row_groups_with_bloom_filter": 0,
     "distinct_encodings": ["PLAIN"], "row_groups_touched_for_cnj_lookup_minmax": 1},
    {"ordering": "date_first", "row_group_count": 9, "row_groups_with_bloom_filter": 0,
     "distinct_encodings": ["PLAIN"], "row_groups_touched_for_cnj_lookup_minmax": 9}
  ],
  "covering_index_needed": false
}
```

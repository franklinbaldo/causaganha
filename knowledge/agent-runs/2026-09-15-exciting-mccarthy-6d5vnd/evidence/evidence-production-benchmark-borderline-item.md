---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6d5vnd-evidence-production-benchmark-borderline-item"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
kind: "runtime_behavior"
reference: "docs/planning/evidence/bloom-filter-a1c-production-borderline-item.json (scripts/benchmarks/bloom_filter_production.py contra djen-2025-12-23/comunicacoes.parquet real, 95.783 linhas)"
summary: "Item de fronteira (1 row group total com ROW_GROUP_SIZE 122880) confirma o mesmo resultado do item grande: nenhuma ordenação ganha bloom filter (PLAIN), e ambas as ordenações trivialmente tocam 1 row group (o arquivo inteiro é 1 grupo) -- covering_index_needed=false, consistente com o item grande."
---

# Evidência: benchmark real (item de fronteira, djen-2025-12-23)

```json
{
  "sample_cnj": "00662078620258160000",
  "sample_cnj_occurrences": 1691,
  "total_rows": 95783,
  "measurements": [
    {"ordering": "cnj_first", "row_group_count": 1, "row_groups_with_bloom_filter": 0,
     "distinct_encodings": ["PLAIN"], "row_groups_touched_for_cnj_lookup_minmax": 1},
    {"ordering": "date_first", "row_group_count": 1, "row_groups_with_bloom_filter": 0,
     "distinct_encodings": ["PLAIN"], "row_groups_touched_for_cnj_lookup_minmax": 1}
  ],
  "covering_index_needed": false
}
```

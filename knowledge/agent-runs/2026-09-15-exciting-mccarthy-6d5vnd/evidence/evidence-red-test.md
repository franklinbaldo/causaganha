---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6d5vnd-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
kind: "test_red"
reference: "tests/test_bloom_filter_production.py::TestDecideCoveringIndex (contra scripts/benchmarks/bloom_filter_production.py com decide_covering_index renomeada temporariamente)"
summary: "Renomeei temporariamente `decide_covering_index` para `_decide_covering_index_disabled_for_red_demo` em scripts/benchmarks/bloom_filter_production.py e rodei `uv run pytest -q tests/test_bloom_filter_production.py`: ImportError na coleta ('cannot import name decide_covering_index from scripts.benchmarks.bloom_filter_production'), confirmando que o teste depende de fato da função pública e falha sem ela antes de restaurar a implementação."
---

# Evidência RED

```
ERROR collecting tests/test_bloom_filter_production.py
ImportError: cannot import name 'decide_covering_index' from
'scripts.benchmarks.bloom_filter_production'
```

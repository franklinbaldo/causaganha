---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6d5vnd-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
kind: "test_green"
reference: "tests/test_bloom_filter_production.py::TestDecideCoveringIndex"
summary: "Restaurada a implementação (`decide_covering_index` pública), `uv run pytest -q tests/test_bloom_filter_production.py` passa com os 3 testes: cnj_first prunando a 1 row group via min/max marca índice covering como desnecessário; cnj_first não prunando a 1 grupo marca como necessário; a decisão usa só a medição cnj_first (date_first é só contraste)."
---

# Evidência GREEN

```
$ uv run pytest -q tests/test_bloom_filter_production.py
...                                                                      [100%]
```

---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-x3954c-evidence-green-dedup-tests"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
kind: "test_green"
reference: "uv run pytest -q tests/segmenter_dataset/test_dedup.py tests/segmenter_dataset/test_splits.py, e depois uv run pytest -q tests/segmenter_dataset (suite completa)"
summary: "Apos a correcao em src/segmenter_dataset/dedup.py (poda por limite de comprimento + quick_ratio, preservando ordem de insercao para a comparacao real), os dois testes novos passam: equivalencia com brute-force em 5 thresholds (0.5/0.7/0.85/0.9/0.95) sobre um corpus sintetico de 18 documentos, e contagem de instanciacao de SequenceMatcher para o cenario curto/longo (poda confirmada). Suite completa tests/segmenter_dataset: 100% verde, 0 falhas (todos os arquivos de teste do pacote)."
---

# Evidência: GREEN — testes novos e suíte completa

```
$ uv run pytest -q tests/segmenter_dataset/test_dedup.py tests/segmenter_dataset/test_splits.py
................................                                         [100%]
```

```
$ uv run pytest -q tests/segmenter_dataset
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
........................................................................ [ 74%]
........................................................................ [ 93%]
...........................                                              [100%]
```

Nenhum teste pré-existente quebrou (a mudança é internamente
transparente para todo chamador — `splits.py` usa apenas o `id_a`/
`id_b`/`ratio` retornados de forma simétrica via `uf.union`, que não
depende de qual lado é `a` vs `b`).

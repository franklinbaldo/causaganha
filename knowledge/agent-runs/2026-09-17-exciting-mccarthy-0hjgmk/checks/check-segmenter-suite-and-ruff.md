---
type: AgentCheck
id: "2026-09-17-exciting-mccarthy-0hjgmk-check-segmenter-suite-and-ruff"
run_id: "2026-09-17-exciting-mccarthy-0hjgmk"
command: "uv run pytest -q tests/segmenter_dataset && uv run ruff check . && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-17-exciting-mccarthy-0hjgmk-evidence-batch17-ingested"
summary: "tests/segmenter_dataset: 100% verde (todos os testes passaram, exit code 0). uv run ruff check .: All checks passed!. uv run ruff format --check .: 453 files already formatted."
---

# Check: suite do segmentador + lint apos ingestao do lote 17

Rodado apos a ingestao real dos 5 documentos do lote 17 em
`data/segmenter`. `uv run pytest -q tests/segmenter_dataset` passou
100% (incluindo `tests/segmenter_dataset/test_segmenter_governance_status.py`,
que le o store real). `uv run ruff check .`/`format --check .` no
repositorio inteiro (incluindo os novos arquivos de evidencia em
`docs/planning/evidence/segmenter-djen-sample-batch17-*`) sem nenhum
apontamento.

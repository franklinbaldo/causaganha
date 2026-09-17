---
type: AgentCheck
id: "2026-09-17-exciting-mccarthy-91jobr-check-segmenter-suite-and-ruff"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
command: "uv run pytest -q tests/segmenter_dataset; uv run pytest -q tests/segmenter_dataset -k batch19; uv run ruff check .; uv run ruff format --check .; uv run python -m scripts.segmenter_semantic_audit --store data/segmenter; uv run python scripts/segmenter_governance_status.py"
result: "passed"
evidence_id: "2026-09-17-exciting-mccarthy-91jobr-evidence-batch19-rescued"
summary: "tests/segmenter_dataset 100% verde (238 testes, incluindo o novo test_real_store_reflects_batch19_corpus_growth adicionado por esta rodada). ruff check/format --check limpos no repositorio inteiro. Audit semantico sem achados novos para os 6 documentos do lote 19. Governance status confirma document_count=155."
---

# Check: suite do segmentador, ruff e auditorias apos o resgate do lote 19

`uv run pytest -q tests/segmenter_dataset -k batch19` verde
isoladamente logo apos adicionar `test_real_store_reflects_batch19_corpus_growth`
a `tests/segmenter_dataset/test_segmenter_governance_status.py`. Em
seguida `uv run pytest -q tests/segmenter_dataset` (suite completa)
tambem 100% verde. `uv run ruff check .` e `uv run ruff format --check .`
limpos no repositorio inteiro (incluindo o arquivo de teste editado).
`uv run python -m scripts.segmenter_semantic_audit --store
data/segmenter` nao aponta nenhum achado novo para os 6 IDs de
documento do lote 19 -- todos os achados existentes pertencem a
documentos pre-existentes. `uv run python
scripts/segmenter_governance_status.py` confirma `document_count=155`,
`annotation_count=208`, `val_ceiling=test_ceiling=23`, batendo com o
`success_signal` do goal.

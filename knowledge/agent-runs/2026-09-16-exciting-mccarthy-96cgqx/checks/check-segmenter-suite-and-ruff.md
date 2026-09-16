---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-96cgqx-check-segmenter-suite-and-ruff"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
command: "uv run ruff check .; uv run ruff format --check .; uv run pytest tests/segmenter_dataset -q; uv run python scripts/segmenter_semantic_audit.py --store data/segmenter"
result: "passed"
evidence_id: "2026-09-16-exciting-mccarthy-96cgqx-evidence-batch13-green-ingested"
summary: "ruff check: All checks passed! ruff format --check: 450 files already formatted. pytest tests/segmenter_dataset -q: 390 passed. segmenter_semantic_audit: 9 findings, all pre-existing (none in the two new batch13 documents)."
---

# Check: suite do segmentador + ruff + audit semantico apos ingestao

Confirma que o lote 13 nao introduziu regressao de estilo nem de teste,
e que o audit semantico nao apontou nenhum achado novo nos dois
documentos ingeridos.

---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-j2t668-check-segmenter-suite-and-ruff"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
command: "uv run pytest -q tests/segmenter_dataset/; uv run ruff check .; uv run ruff format --check .; uv run python scripts/segmenter_semantic_audit.py --store data/segmenter; uv run python scripts/segmenter_governance_status.py"
result: "passed"
evidence_id: "2026-09-16-exciting-mccarthy-j2t668-evidence-batch15-ingested"
summary: "pytest: 100% pass (all dots across the full run, exit code 0, no F/E markers), including the new test_real_store_reflects_batch15_corpus_growth regression test. ruff check/format: clean on all touched files. Semantic audit: 9 findings total, all either already-allowlisted from prior batches or on pre-existing (non-batch15) document hashes -- zero new findings from this batch's 6 documents. Governance status: document_count=132, annotation_count=185, val_ceiling=test_ceiling=20."
---

# Check: suite do segmentador, ruff e audit semantico apos o lote 15

Rodado apos a ingestao bem-sucedida dos 6 documentos do lote 15.
`uv run pytest -q tests/segmenter_dataset/` completou com 100% de pontos
(nenhum `F`/`E` na saida, exit code 0 confirmado pela notificacao do
comando em background), incluindo o novo teste de regressao
`test_real_store_reflects_batch15_corpus_growth` que trava os 6 hashes
de documento deste lote. `uv run ruff check`/`format --check` limpos nos
arquivos tocados (script de teste, evidencias). O audit semantico
(`scripts/segmenter_semantic_audit.py`) sinalizou 9 achados no total,
todos verificados individualmente contra a allowlist de testes
existente ou confirmados como pertencentes a documentos de rodadas
anteriores (nenhum dos 6 hashes deste lote aparece na lista de
achados). `scripts/segmenter_governance_status.py` confirma
`document_count=132`, `val_ceiling=test_ceiling=20`.

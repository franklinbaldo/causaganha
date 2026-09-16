---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-imy2ed-check-segmenter-suite-and-governance"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
command: "uv run pytest tests/segmenter_dataset -q && uv run ruff check . && uv run ruff format --check src scripts tests && uv run python scripts/segmenter_governance_status.py && uv run python scripts/segmenter_category_support.py && uv run python scripts/segmenter_semantic_audit.py --store data/segmenter"
result: "passed"
evidence_id: "2026-09-16-exciting-mccarthy-imy2ed-evidence-batch10-ingested"
summary: "tests/segmenter_dataset -q: 375 testes coletados, todos verdes, incluindo o novo test_real_store_reflects_batch10_corpus_growth (RED antes da ingestao real, GREEN depois). ruff check .: All checks passed. ruff format --check: 441 arquivos ja formatados. segmenter_governance_status.py: document_count 111, val_ceiling/test_ceiling 17/17, corpus_scale_blocks_floor ainda true (esperado). segmenter_category_support.py: todas as 25 categorias acima do piso de 10 (preliminar sobe de 21 para 23). segmenter_semantic_audit.py --store data/segmenter: nenhum achado novo nos dois documentos do lote 10."
---

# Check: suite do segmentador, lint e diagnosticos apos o lote 10

Todos os comandos listados foram executados sequencialmente apos a
ingestao real; nenhum falhou.

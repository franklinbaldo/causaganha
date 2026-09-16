---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-la7bsl-check-full-suite"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
goal_id: "2026-09-16-exciting-mccarthy-la7bsl-goal-djen-sample-batch5"
command: "uv run ruff check; uv run ruff format --check; uv run pytest -q -k segmenter; uv run python scripts/segmenter_semantic_audit.py; uv run python scripts/segmenter_governance_status.py (before/after)"
result: "passed"
evidence_id: "2026-09-16-exciting-mccarthy-la7bsl-evidence-batch5-ingested"
summary: "ruff check: all checks passed. ruff format --check: 450 files already formatted. pytest -k segmenter: 341 passed, 0 failed. semantic audit: 7 pre-existing findings, none on this batch's new document ids. Governance: document_count 86->93, val_ceiling/test_ceiling 13->14, TJMS added as 25th tribunal."
---

# Check: suite completa apos ingestao do lote 5

Ruff (check + format), suite de testes do segmentador, audit semantico
e governance status todos rodados apos a ingestao real -- nenhuma
regressao, `document_count` cresceu de 86 para 93.

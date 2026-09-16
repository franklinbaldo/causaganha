---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-5lvbii-check-batch12-green-and-audit"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
goal_id: "2026-09-16-exciting-mccarthy-5lvbii-goal-djen-sample-batch12"
evidence_id: "2026-09-16-exciting-mccarthy-5lvbii-evidence-batch12-ingested"
command: "uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch12_corpus_growth -q && PYTHONPATH=. uv run python scripts/segmenter_semantic_audit.py --store data/segmenter && uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "test_real_store_reflects_batch12_corpus_growth: GREEN (was RED at 119<121, now passes at 121 documents). Semantic audit reports 9 findings, all pre-existing (doc IDs doc_2a07306d/3b0be436/3cffd796/b0c36490/b8a4a405/c502b14f/c7724144/d61aecbf/f985597a) and already covered by tests/segmenter_dataset/test_segmenter_audit_scripts.py's allowlist -- neither new document (doc_f3b730a0.../doc_d9de18ae...) appears, confirming no new findings from this batch. ruff check: All checks passed. ruff format --check: 450 files already formatted."
---

# Check: GREEN do lote 12 e audit semântico

Teste de regressão verde após a ingestão. Audit semântico não introduz
nenhum achado novo (os 9 achados existentes já pertencem a documentos de
lotes anteriores, cobertos pela allowlist). Ruff limpo.

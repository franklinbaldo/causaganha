---
type: "RunCheck"
id: "run-checks/20260916t162542z-do-the-best-useful-work-availab/check-verification-batch11"
run: "runs/20260916T162542Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/segmenter_dataset/tests/segmenter_dataset/test_segmenter_governance_status.py -k batch11; uv run pytest -q tests/segmenter_dataset/; uv run ruff check .; uv run ruff format --check .; uv run python scripts/segmenter_semantic_audit.py --store data/segmenter; uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "test_real_store_reflects_batch11_corpus_growth passou (GREEN). Suite completa tests/segmenter_dataset/ passou (exit 0, todos os pontos verdes). ruff check/format limpos. Audit semantico sem novos achados para os dois documentos novos. okf-parser check conformant (1910 concepts, 0 diagnostics)."
status: "pass"
evidence: "run-evidence/20260916t162542z-do-the-best-useful-work-availab/evidence-batch11-ingested"
---

# RunCheck
